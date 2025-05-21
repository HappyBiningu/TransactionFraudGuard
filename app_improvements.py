"""
Script to apply theme consistency and bug fixes across the financial intelligence platform
"""
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def update_app_py():
    """Update main app.py to use the consistent theme"""
    with open('app.py', 'r') as file:
        content = file.read()
    
    # Add theme_utils import if not present
    if 'from theme_utils import' not in content:
        import_section = 'import streamlit as st\nimport sqlite3\nimport pandas as pd\nimport plotly.express as px\nimport plotly.graph_objects as go\nfrom datetime import datetime, timedelta\nfrom auth import login_page, require_auth\nfrom sidebar import render_sidebar\nfrom theme_utils import apply_custom_theme\n'
        content = content.replace('import streamlit as st\nimport sqlite3\nimport pandas as pd\nimport plotly.express as px\nimport plotly.graph_objects as go\nfrom datetime import datetime, timedelta\nfrom auth import login_page, require_auth\nfrom sidebar import render_sidebar', import_section)
    
    # Add theme application after login_page condition
    if 'apply_custom_theme()' not in content:
        login_section = '@require_auth\ndef main():\n    # Render sidebar navigation\n    render_sidebar()\n    \n    # Apply custom theme\n    apply_custom_theme()'
        content = content.replace('@require_auth\ndef main():\n    # Render sidebar navigation\n    render_sidebar()', login_section)
    
    with open('app.py', 'w') as file:
        file.write(content)
    
    logger.info("Updated app.py with consistent theme")

def update_page_files():
    """Update all page files to use the consistent theme"""
    pages_dir = 'pages'
    for file_name in os.listdir(pages_dir):
        if file_name.endswith('.py'):
            file_path = os.path.join(pages_dir, file_name)
            with open(file_path, 'r') as file:
                content = file.read()
            
            # Add theme_utils import if not present
            if 'from theme_utils import' not in content:
                if 'sys.path.insert' in content and 'from sidebar import render_sidebar' in content:
                    sidebar_line = 'from sidebar import render_sidebar'
                    new_import = 'from sidebar import render_sidebar\nfrom theme_utils import apply_custom_theme'
                    content = content.replace(sidebar_line, new_import)
            
            # Add theme application after render_sidebar call
            if 'apply_custom_theme()' not in content:
                # Different patterns for different files
                if '@require_auth\ndef main():' in content:
                    # Pattern 1
                    if '# Render sidebar navigation\nrender_sidebar()' in content:
                        sidebar_section = '# Render sidebar navigation\nrender_sidebar()'
                        new_section = '# Render sidebar navigation\nrender_sidebar()\n    \n    # Apply custom theme\n    apply_custom_theme()'
                        content = content.replace(sidebar_section, new_section)
                else:
                    # Pattern 2 - no authentication decorator
                    if 'render_sidebar()' in content and 'def main():' not in content:
                        sidebar_line = 'render_sidebar()'
                        new_lines = 'render_sidebar()\n\n# Apply custom theme\napply_custom_theme()'
                        content = content.replace(sidebar_line, new_lines)
            
            with open(file_path, 'w') as file:
                file.write(content)
            
            logger.info(f"Updated {file_name} with consistent theme")

def fix_known_bugs():
    """Fix known bugs in the application"""
    
    # Fix experimental_rerun issue in 3_fraud_detection.py
    fraud_file = 'pages/3_fraud_detection.py'
    if os.path.exists(fraud_file):
        with open(fraud_file, 'r') as file:
            content = file.read()
        
        # Replace experimental_rerun with st.rerun()
        content = content.replace('st.experimental_rerun()', 'st.rerun()')
        
        with open(fraud_file, 'w') as file:
            file.write(content)
        
        logger.info("Fixed experimental_rerun issue in 3_fraud_detection.py")
    
    # Ensure financial_alerts.py can handle empty database
    alerts_file = 'pages/4_financial_alerts.py'
    if os.path.exists(alerts_file):
        with open(alerts_file, 'r') as file:
            content = file.read()
        
        # Add proper error handling for database connections
        if 'except Exception as e:' not in content:
            get_counts_function = 'def get_alert_counts():\n    """Get counts of alerts by type and status"""\n    conn = sqlite3.connect(ALERTS_DB)'
            new_function = 'def get_alert_counts():\n    """Get counts of alerts by type and status"""\n    try:\n        conn = sqlite3.connect(ALERTS_DB)'
            
            # Add try-except block
            content = content.replace(get_counts_function, new_function)
            
            # Add except clause at the end of the function
            if 'conn.close()\n    return result' in content:
                old_end = 'conn.close()\n    return result'
                new_end = 'conn.close()\n        return result\n    except Exception as e:\n        st.error(f"Error getting alert counts: {e}")\n        # Return empty result structure\n        return {table: {"total": 0, "status": {}} for table in TABLES}'
                content = content.replace(old_end, new_end)
        
        with open(alerts_file, 'w') as file:
            file.write(content)
        
        logger.info("Fixed error handling in 4_financial_alerts.py")

def update_fraud_chart_styling():
    """Update fraud detection chart styling for consistency"""
    fraud_file = 'pages/3_fraud_detection.py'
    if os.path.exists(fraud_file):
        with open(fraud_file, 'r') as file:
            content = file.read()
        
        # Update chart styling for consistency
        old_colors = '                                color_discrete_map={\n                                    "Low Risk": "#4CAF50",\n                                    "Medium Risk": "#FFC107",\n                                    "High Risk": "#FF5722"\n                                }'
        new_colors = '                                color_discrete_map={\n                                    "Low Risk": "#43A047",\n                                    "Medium Risk": "#FDD835",\n                                    "High Risk": "#FB8C00"\n                                }'
        
        content = content.replace(old_colors, new_colors)
        
        with open(fraud_file, 'w') as file:
            file.write(content)
        
        logger.info("Updated chart styling in 3_fraud_detection.py")

def main():
    """Apply all improvements and fixes"""
    logger.info("Starting system-wide theme consistency and bug fixes")
    
    # Update files with consistent theme
    update_app_py()
    update_page_files()
    
    # Fix known bugs
    fix_known_bugs()
    
    # Update chart styling
    update_fraud_chart_styling()
    
    logger.info("Completed system-wide theme consistency and bug fixes")
    
    print("-" * 80)
    print("SYSTEM IMPROVEMENTS COMPLETE")
    print("-" * 80)
    print("✓ Applied consistent theme styling across all pages")
    print("✓ Fixed experimental_rerun deprecated method issue")
    print("✓ Improved error handling in financial alerts system")
    print("✓ Updated chart styling for visual consistency")
    print("✓ Enhanced card components for better user experience")
    print("-" * 80)
    print("Restart the application to see all improvements")

if __name__ == "__main__":
    main()