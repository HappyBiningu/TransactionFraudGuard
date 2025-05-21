"""
Shared theme utilities for the Unified Financial Intelligence Platform.
This module provides consistent styling and theme elements across all pages.
"""
import streamlit as st

def apply_custom_theme():
    """Apply consistent custom theme styling across all pages"""
    
    # Define the color palette
    colors = {
        "primary": "#2563EB",       # Main blue color
        "primary_light": "#3B82F6",
        "primary_dark": "#1E40AF",
        "secondary": "#059669",     # Green for positive trends
        "secondary_light": "#10B981",
        "warning": "#F59E0B",       # Amber for warnings
        "danger": "#DC2626",        # Red for alerts/danger
        "neutral": "#64748B",       # Slate for neutral elements
        "neutral_light": "#94A3B8",
        "background": "#F8FAFC",    # Very light blue-gray
        "card_bg": "#FFFFFF",
        "text": "#1E293B",          # Dark blue-gray for text
        "text_light": "#64748B"
    }
    
    # Apply custom CSS
    st.markdown(f"""
    <style>
        /* Global Theme Settings */
        :root {{
            --primary-color: {colors["primary"]};
            --primary-color-light: {colors["primary_light"]};
            --primary-dark: {colors["primary_dark"]};
            --secondary-color: {colors["secondary"]};
            --secondary-light: {colors["secondary_light"]};
            --warning-color: {colors["warning"]};
            --danger-color: {colors["danger"]};
            --neutral-color: {colors["neutral"]};
            --neutral-light: {colors["neutral_light"]};
            --background-color: {colors["background"]};
            --card-background: {colors["card_bg"]};
            --text-color: {colors["text"]};
            --text-light: {colors["text_light"]};
            
            --border-radius: 0.5rem;
            --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --card-shadow-hover: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }}
        
        /* Main Container */
        .main .block-container {{
            padding-top: 2rem;
            padding-bottom: 2rem;
        }}
        
        /* Section Headers */
        .section-header {{
            text-align: center;
            color: var(--primary-dark);
            margin-bottom: 1.5rem;
            font-weight: 600;
            font-size: 1.5rem;
            position: relative;
            padding-bottom: 0.75rem;
        }}
        
        .section-header::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 100px;
            height: 3px;
            background: linear-gradient(90deg, rgba(59,130,246,0.1) 0%, rgba(37,99,235,1) 50%, rgba(59,130,246,0.1) 100%);
            border-radius: 3px;
        }}
        
        /* Enhanced Metric Cards */
        .enhanced-metric-card {{
            background-color: var(--card-background);
            border-radius: var(--border-radius);
            padding: 1.25rem;
            box-shadow: var(--card-shadow);
            margin-bottom: 1rem;
            transition: all 0.3s ease;
            border-left: 4px solid var(--primary-color);
        }}
        
        .enhanced-metric-card:hover {{
            box-shadow: var(--card-shadow-hover);
            transform: translateY(-2px);
        }}
        
        .enhanced-metric-card.success-card {{
            border-left-color: var(--secondary-color);
        }}
        
        .enhanced-metric-card.warning-card {{
            border-left-color: var(--warning-color);
        }}
        
        .enhanced-metric-card.danger-card {{
            border-left-color: var(--danger-color);
        }}
        
        .metric-card-header {{
            display: flex;
            align-items: center;
            margin-bottom: 0.75rem;
        }}
        
        .metric-card-icon {{
            font-size: 1.25rem;
            margin-right: 0.75rem;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: rgba(59, 130, 246, 0.1);
            border-radius: 50%;
            color: var(--primary-color);
        }}
        
        .success-card .metric-card-icon {{
            background-color: rgba(5, 150, 105, 0.1);
            color: var(--secondary-color);
        }}
        
        .warning-card .metric-card-icon {{
            background-color: rgba(245, 158, 11, 0.1);
            color: var(--warning-color);
        }}
        
        .danger-card .metric-card-icon {{
            background-color: rgba(220, 38, 38, 0.1);
            color: var(--danger-color);
        }}
        
        .metric-card-title {{
            font-weight: 600;
            color: var(--text-color);
            font-size: 1rem;
        }}
        
        .metric-card-body {{
            padding: 0.5rem 0;
        }}
        
        .primary-metric {{
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--primary-dark);
            margin-bottom: 0.25rem;
        }}
        
        .success-card .primary-metric {{
            color: var(--secondary-color);
        }}
        
        .warning-card .primary-metric {{
            color: var(--warning-color);
        }}
        
        .danger-card .primary-metric {{
            color: var(--danger-color);
        }}
        
        .metric-label {{
            font-size: 0.875rem;
            color: var(--neutral-color);
            margin-bottom: 0.75rem;
        }}
        
        .metric-details {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.75rem;
        }}
        
        .secondary-metric {{
            display: flex;
            flex-direction: column;
        }}
        
        .secondary-value {{
            font-weight: 600;
            color: var(--text-color);
            font-size: 0.95rem;
        }}
        
        .secondary-label {{
            font-size: 0.75rem;
            color: var(--text-light);
        }}
        
        .metric-trend {{
            display: flex;
            align-items: center;
            padding: 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.875rem;
            background-color: rgba(100, 116, 139, 0.1);
        }}
        
        .trend-up {{
            background-color: rgba(5, 150, 105, 0.1);
            color: var(--secondary-color);
        }}
        
        .trend-down {{
            background-color: rgba(220, 38, 38, 0.1);
            color: var(--danger-color);
        }}
        
        .trend-neutral {{
            background-color: rgba(100, 116, 139, 0.1);
            color: var(--neutral-color);
        }}
        
        .trend-icon {{
            margin-right: 0.5rem;
        }}
        
        .trend-value {{
            font-weight: 600;
            margin-right: 0.5rem;
        }}
        
        .trend-period {{
            color: var(--text-light);
            font-size: 0.75rem;
        }}
        
        /* Data Tables */
        .enhanced-table {{
            background-color: var(--card-background);
            border-radius: var(--border-radius);
            overflow: hidden;
            box-shadow: var(--card-shadow);
        }}
        
        /* Charts */
        .chart-container {{
            background-color: var(--card-background);
            border-radius: var(--border-radius);
            padding: 1rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--card-shadow);
        }}
        
        .chart-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--primary-dark);
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #E5E7EB;
        }}
        
        /* Buttons */
        .custom-button {{
            display: inline-block;
            padding: 0.5rem 1rem;
            font-weight: 500;
            text-align: center;
            background-color: var(--primary-color);
            color: white;
            border-radius: var(--border-radius);
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            transition: all 0.2s ease;
            cursor: pointer;
            border: none;
        }}
        
        .custom-button:hover {{
            background-color: var(--primary-dark);
            box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.1);
        }}
        
        .custom-button.secondary {{
            background-color: var(--secondary-color);
        }}
        
        .custom-button.secondary:hover {{
            background-color: #047857;
        }}
        
        .custom-button.outline {{
            background-color: transparent;
            color: var(--primary-color);
            border: 1px solid var(--primary-color);
        }}
        
        .custom-button.outline:hover {{
            background-color: rgba(59, 130, 246, 0.1);
        }}
        
        /* Sidebar styling */
        .css-6qob1r.e1fqkh3o3 {{
            background-color: #1E293B;
        }}
        
        /* Custom alert boxes */
        .custom-alert {{
            padding: 1rem;
            border-radius: var(--border-radius);
            margin-bottom: 1rem;
            font-size: 0.875rem;
        }}
        
        .custom-alert.info {{
            background-color: rgba(59, 130, 246, 0.1);
            border-left: 4px solid var(--primary-color);
            color: var(--primary-dark);
        }}
        
        .custom-alert.success {{
            background-color: rgba(5, 150, 105, 0.1);
            border-left: 4px solid var(--secondary-color);
            color: var(--secondary-color);
        }}
        
        .custom-alert.warning {{
            background-color: rgba(245, 158, 11, 0.1);
            border-left: 4px solid var(--warning-color);
            color: var(--warning-color);
        }}
        
        .custom-alert.error {{
            background-color: rgba(220, 38, 38, 0.1);
            border-left: 4px solid var(--danger-color);
            color: var(--danger-color);
        }}
        
        /* Custom tabs styling */
        div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button[role="tab"] {{
            background-color: transparent;
            color: var(--text-color);
            border-radius: 0;
            border-bottom: 2px solid transparent;
            padding: 0.5rem 1rem;
        }}
        
        div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button[role="tab"][aria-selected="true"] {{
            background-color: transparent;
            color: var(--primary-color);
            border-bottom: 2px solid var(--primary-color);
            font-weight: 600;
        }}
        
        div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button[role="tab"]:hover {{
            background-color: rgba(59, 130, 246, 0.05);
            color: var(--primary-color);
            border-radius: var(--border-radius) var(--border-radius) 0 0;
        }}
        
        /* Status indicators */
        .status-indicator {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
        }}
        
        .status-active, .status-complete, .status-success {{
            background-color: rgba(5, 150, 105, 0.1);
            color: var(--secondary-color);
        }}
        
        .status-pending, .status-warning {{
            background-color: rgba(245, 158, 11, 0.1);
            color: var(--warning-color);
        }}
        
        .status-inactive, .status-error, .status-danger {{
            background-color: rgba(220, 38, 38, 0.1);
            color: var(--danger-color);
        }}
        
        .status-neutral, .status-info {{
            background-color: rgba(59, 130, 246, 0.1);
            color: var(--primary-color);
        }}
    </style>
    """, unsafe_allow_html=True)

def render_metric_card(title, value, description=None, trend=None, trend_direction=None, 
                      icon="📊", card_type="primary"):
    """
    Render a consistent metric card with optional trend indicator
    
    Parameters:
    -----------
    title : str
        The title of the metric card
    value : str or int or float
        The primary value to display
    description : str, optional
        Additional description text
    trend : float, optional
        Trend percentage value
    trend_direction : str, optional
        Direction of trend: 'up', 'down', or 'neutral'
    icon : str, optional
        Emoji or icon character to display
    card_type : str, optional
        Card style: 'primary', 'success', 'warning', or 'danger'
    """
    
    # Format value if it's a number
    if isinstance(value, (int, float)):
        if isinstance(value, int):
            formatted_value = f"{value:,}"
        else:
            formatted_value = f"{value:,.2f}"
    else:
        formatted_value = value
    
    # Determine card class
    if card_type == "success":
        card_class = "success-card"
    elif card_type == "warning":
        card_class = "warning-card"
    elif card_type == "danger":
        card_class = "danger-card"
    else:
        card_class = ""
    
    # Determine trend class and icon
    trend_class = ""
    trend_icon = ""
    
    if trend_direction:
        if trend_direction == "up":
            trend_class = "trend-up"
            trend_icon = "📈"
        elif trend_direction == "down":
            trend_class = "trend-down"
            trend_icon = "📉"
        else:
            trend_class = "trend-neutral"
            trend_icon = "⚖️"
    
    # Build the HTML for the card
    html = f"""
    <div class="enhanced-metric-card {card_class}">
        <div class="metric-card-header">
            <div class="metric-card-icon">{icon}</div>
            <div class="metric-card-title">{title}</div>
        </div>
        <div class="metric-card-body">
            <div class="primary-metric">{formatted_value}</div>
            <div class="metric-label">{description or ""}</div>
    """
    
    # Add trend if provided
    if trend is not None:
        html += f"""
            <div class="metric-trend {trend_class}">
                <span class="trend-icon">{trend_icon}</span>
                <span class="trend-value">{abs(trend):.1f}%</span>
                <span class="trend-period">change</span>
            </div>
        """
    
    # Close the card
    html += """
        </div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)

def create_alerts(alert_type, message):
    """
    Create styled alert boxes for different alert types
    
    Parameters:
    -----------
    alert_type : str
        Type of alert: 'info', 'success', 'warning', or 'error'
    message : str
        Alert message to display
    """
    st.markdown(f"""
    <div class="custom-alert {alert_type}">
        {message}
    </div>
    """, unsafe_allow_html=True)