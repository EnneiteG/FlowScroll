import logging
from PyQt6.QtCore import QThread, pyqtSignal
from src.core.version import APP_VERSION, GITHUB_REPO

try:
    import requests
except ImportError:
    requests = None

class UpdateChecker(QThread):
    check_finished = pyqtSignal(bool, str, str) # found_update, version_string, url

    def run(self):
        if not requests:
            self.check_finished.emit(False, "", "")
            return
            
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            # SECURITY: Enforce HTTPS using requests verification
            response = requests.get(url, timeout=10, verify=True)
            
            if response.status_code == 200:
                data = response.json()
                tag_name = data.get("tag_name", "").lstrip("v") # e.g. "0.1.1"
                html_url = data.get("html_url", "")
                
                # Check for insecure URL
                if html_url and not html_url.startswith("https://"):
                    logging.warning(f"Insecure update URL detected: {html_url}")
                    self.check_finished.emit(False, "", "")
                    return

                if tag_name:
                    if self.is_version_greater(tag_name, APP_VERSION):
                        self.check_finished.emit(True, tag_name, html_url)
                    else:
                        # Success but no update
                        self.check_finished.emit(False, tag_name, "")
                else:
                    self.check_finished.emit(False, APP_VERSION, "")
            else:
                 self.check_finished.emit(False, "", "")
                 
        except Exception as e:
            logging.warning(f"Update check failed: {e}")
            self.check_finished.emit(False, "", "")

    def is_version_greater(self, remote, current):
        try:
            # Parse versions like 1.0.2 into lists of ints for comparison
            # Split by '.' and filter out non-digits if needed, but simple split works for 1.0.0
            def parse(v):
                return [int(p) for p in v.split('.') if p.isdigit()]
                
            r_parts = parse(remote)
            c_parts = parse(current)
            
            # Simple list comparison works: [0, 1, 10] > [0, 1, 9] is True
            return r_parts > c_parts
        except ValueError:
            # Fallback to string comparison if parsing fails
            return remote > current
