dashboard_theme = [
    {
        "selector": "body",
        "props": [
            ("background-color", "#f8f9fa"), # Lighter background
            ("font-family", "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"), # Modern font stack
            ("margin", "0"),
            ("padding", "0"),
            ("color", "#212529") # Darker text for better contrast
        ]
    },
    {
        "selector": ".dash-tabs-container", # Style for dcc.Tabs container
        "props": [
            ("background-color", "#e9ecef"),
        ]
    },
    {
        "selector": ".dash-tab", # Style for individual tabs
        "props": [
            ("padding", "10px"),
            ("border-radius", "4px 4px 0 0"),
        ]
    },
    {
        "selector": ".dash-tab--selected",
        "props": [
            ("background-color", "#f8f9fa"),
            ("border-color", "#dee2e6 #dee2e6 #f8f9fa"), # Match background for selected tab "underline"
            ("font-weight", "bold"),
        ]
    },
    {
        "selector": "h1, h2, h3, h4, h5, h6", # Headers
        "props": [
            ("color", "#007bff"), # Primary color for headers
            ("margin-top", "10px"),
            ("margin-bottom", "10px"),
        ]
    },
    {
        "selector": ".dash-dropdown", # Dropdowns
        "props": [
            ("margin-bottom", "10px"),
        ]
    },
    {
        "selector": "button, .button", # Buttons
        "props": [
            ("background-color", "#007bff"),
            ("color", "white"),
            ("border", "none"),
            ("padding", "10px 15px"),
            ("text-align", "center"),
            ("text-decoration", "none"),
            ("display", "inline-block"),
            ("font-size", "14px"),
            ("margin", "4px 2px"),
            ("cursor", "pointer"),
            ("border-radius", "4px"),
        ]
    },
    {
        "selector": "button:hover, .button:hover",
        "props": [
            ("background-color", "#0056b3"),
        ]
    },
    {
        "selector": "input[type=text], textarea", # Text inputs and textareas
        "props": [
            ("padding", "8px"),
            ("border", "1px solid #ced4da"),
            ("border-radius", "4px"),
            ("box-sizing", "border-box"),
        ]
    },
    {
        "selector": "#chat-history", # Specific style for chat history
        "props": [
            ("border", "1px solid #ced4da"),
            ("background-color", "#ffffff"),
            ("padding", "10px"),
            ("border-radius", "4px"),
            ("overflow-y", "auto"), # Make it scrollable
            ("font-size", "0.9em")
        ]
    },
    { # Main control panel and map panel styling
        "selector": ".control-panel",
        "props": [
            ("background-color", "#ffffff"),
            ("padding", "20px"), # Original had 2em, making it consistent
            ("border-radius", "8px"),
            ("box-shadow", "0 4px 8px rgba(0,0,0,0.05)")
        ]
    },
    {
        "selector": ".map-panel",
        "props": [
             ("background-color", "#ffffff"),
             ("padding", "20px"),
             ("border-radius", "8px"),
             ("box-shadow", "0 4px 8px rgba(0,0,0,0.05)")
        ]
    }
]