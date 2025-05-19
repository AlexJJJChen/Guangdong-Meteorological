import os
import rasterio
import geopandas as gpd
import json
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.mask import mask

# ========== 本地地理高程与土地利用数据读取 ==========

def check_tif_value_range(tif_path):
    """
    获取tif文件的最小最大值
    """
    with rasterio.open(tif_path) as src:
        band = src.read(1)
        min_val = band.min()
        max_val = band.max()
    print(f"{tif_path} value range: min={min_val}, max={max_val}")
    return min_val, max_val

def check_shp_attributes(shp_path):
    """
    展示shp文件的属性表字段和前几行
    """
    gdf = gpd.read_file(shp_path)
    print("SHP属性字段:", list(gdf.columns))
    print(gdf.head())
    return gdf.columns, gdf.head()


def reproject_raster(src_tif, dst_tif, target_crs):
    with rasterio.open(src_tif) as src:
        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': target_crs,
            'transform': transform,
            'width': width,
            'height': height
        })
        with rasterio.open(dst_tif, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.nearest
                )
    print(f"[!] 已重投影到：{dst_tif}")

# ========== 构建低地指数 ==========

def calc_lowland_index(dem_arr, province_lowland_threshold, na_value=-32768):
    """
    根据全省统一低地高程阈值，计算该城市的低地指数（低于阈值的像元比例）
    :param dem_arr: np.ndarray, 城市的DEM数组
    :param province_lowland_threshold: float, 全省低地分位阈值
    :param na_value: float/int, DEM缺失值
    :return: float, 该城市低地指数（0-1之间）
    """
    arr = np.copy(dem_arr).astype(float)
    arr[arr == na_value] = np.nan
    # 计算低地掩模
    lowland_mask = np.where(arr <= province_lowland_threshold, 1, 0)
    # 低地指数 = 低地像元比例
    lowland_index = np.nanmean(lowland_mask)
    return lowland_index


# ========== 计算城市不透水面比例 ==========
def region_landuse_stats(masked_landuse_arr):
    """统计区域(掩模内)各土地类型占比（剔除0与nodata）"""
    nonzero = masked_landuse_arr[masked_landuse_arr > 0]
    if len(nonzero) == 0:
        return {}
    unique, counts = np.unique(nonzero, return_counts=True)
    total = np.sum(counts)
    fractions = {int(u): int(c)/total for u, c in zip(unique, counts)}
    return fractions

def impervious_fraction(landuse_stats):
    """不透水面比例，类目8代表不透水"""
    return landuse_stats.get(8, 0.0)

# ========== 区域地图截取 ==========
def get_city_mask(city_shp, city_name, target_raster):
    """根据地级市名裁剪栅格数据，返回掩模和仿射变换"""
    gdf = gpd.read_file(city_shp)
    gdf = gdf[gdf['地级'] == city_name]
    with rasterio.open(target_raster) as src:
        out_image, out_transform = mask(src, gdf.geometry, crop=True)
        out_image = out_image.squeeze()
        return out_image, out_transform

# --------- 火灾风险相关参数 ---------
LANDUSE_WEIGHTS = {
    1: 1.0,   # Cropland
    2: 1.5,   # Forest
    3: 1.5,   # Shrub
    4: 1.0,   # Grassland
    5: 0.0,   # Water
    6: 0.0,   # Snow/Ice
    7: 0.0,   # Barren
    8: 1.2,   # Impervious (城市高密度)
    9: 0.8    # Wetland
}

def calc_fire_risk_weight(landuse_stats, landuse_weights):
    """各土地利用类型比例加权，得到火灾风险权重。"""
    fire_risk = 0.0
    for landuse_type, frac in landuse_stats.items():
        weight = landuse_weights.get(landuse_type, 0.0)
        fire_risk += frac * weight
    return fire_risk



# ========== main ==========

if __name__ == "__main__":

    # --- DEM与土地利用本地数据 ---
    dem_tif_path = "../data/dem/广东高程数据1.tif"
    landuse_tif_path = "../data/landuse/CLCD_v01_2023_albert_guangdong.tif"
    city_shp_path = "../data/admin_unit/地级.shp"

    # 检查DEM高程范围
    check_tif_value_range(dem_tif_path)
    # 检查土地利用分布
    check_tif_value_range(landuse_tif_path)
    # 查看行政区划信息
    check_shp_attributes(city_shp_path)

    # 读取shp并筛选广东省
    gdf = gpd.read_file(city_shp_path)
    gd_gdf = gdf[gdf['省级'] == "广东省"].copy()
    # 与API的坐标系相统一： WGS84
    if gd_gdf.crs != 'EPSG:4326':
        gd_gdf = gd_gdf.to_crs(epsg=4326)

    gd_gdf.to_file('../data/admin_unit/guangdong_border.geojson', driver='GeoJSON', encoding='utf-8')

    # 计算几何中心用于API定位
    gd_gdf['centroid'] = gd_gdf.geometry.centroid
    gd_gdf['lon'] = gd_gdf['centroid'].x
    gd_gdf['lat'] = gd_gdf['centroid'].y


    # 统一栅格数据投影（以地级市shp为基准）
    target_crs = gd_gdf.crs
    # 处理DEM
    dem_reproj_path = '../data/dem/guangdong_dem_reproj.tif'
    if not os.path.exists(dem_reproj_path):
        reproject_raster(dem_tif_path, dem_reproj_path, target_crs)
    # 处理土地利用
    landuse_reproj_path = '../data/landuse/guangdong_landuse_reproj.tif'
    if not os.path.exists(landuse_reproj_path):
        reproject_raster(landuse_tif_path, landuse_reproj_path, target_crs)


    # 计算全省DEM低地阈值
    with rasterio.open(dem_reproj_path) as src:
        dem_data = src.read(1)
        na_value = -32768
        # 剔除缺失值
        valid_dem_flat = dem_data[dem_data != na_value]
        province_lowland_threshold = np.percentile(valid_dem_flat, 30)
        print(f"全省低地阈值 ({30}%) = (m)", province_lowland_threshold)

    # 计算并合并低地指数
    cities_meta = []

    for idx, row in gd_gdf.iterrows():
        city_name = row['地级']
        adcode = row['地级码']
        lon = row['lon']
        lat = row['lat']

        # -- 新增：城市区域DEM和土地覆盖裁剪 --
        dem_arr, _ = get_city_mask(city_shp_path, city_name, dem_reproj_path)
        landuse_arr, _ = get_city_mask(city_shp_path, city_name, landuse_reproj_path)

        # 低地指数
        lowland_index = calc_lowland_index(dem_arr, province_lowland_threshold, na_value=na_value)
        print(f"{city_name} 低地指数: {lowland_index:.3f}")

        # 计算各土地利用比例与不透水面比例
        landuse_stats = region_landuse_stats(landuse_arr)
        imperv_frac = float(impervious_fraction(landuse_stats))
        print(f"{city_name} 不透水面比例: {imperv_frac:.3f}")

        # 火灾风险权重计算
        fire_risk_weight = calc_fire_risk_weight(landuse_stats, LANDUSE_WEIGHTS)
        print(f"{city_name} 火灾风险权重: {fire_risk_weight:.3f}")

        meta = {
            'city_name': city_name,
            'adcode': adcode,
            'lon': lon,
            'lat': lat,
            'lowland_index': lowland_index,
            'impervious_frac': imperv_frac,
            'fire_risk_weight': fire_risk_weight
        }
        cities_meta.append(meta)

    with open('../data/admin_unit/guangdong_cities_meta.json', 'w', encoding='utf-8') as f:
        json.dump(cities_meta, f, ensure_ascii=False, indent=2)

    print("guangdong_cities_meta.json 已保存，")