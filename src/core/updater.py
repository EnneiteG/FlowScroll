import logging
import time
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
            # requests verifies SSL certificates by default (verify=True)
            # We explicitly set it just to be sure and compliant
            response = requests.get(url, timeout=10, verify=True)
            
            if response.status_code == 200:
                data = response.json()
                tag_name = data.get("tag_name", "").lstrip("v")
                # Ensure the download/view URL is also HTTPS
                html_url = data.get("html_url", "")
                if html_url and not html_url.startswith("https://"):
                    logging.warning(f"Insecure update URL detected: {html_url}")
                    return

                if tag_name and tag_name != APP_VERSION:
                    # Compare versions properly
                    # Check if remote version is strictly greater
                    if self.is_version_greater(tag_name, APP_VERSION):
                        self.check_finished.emit(True, tag_name, html_url)
                    else:
                        self.check_finished.emit(False, tag_name, "")
                else:
                    self.check_finished.emit(False, APP_VERSION, "")

    def is_version_greater(self, remote, current):
        try:
            r_parts = [int(p) for p in remote.split('.')]
            c_parts = [int(p) for p in current.split('.')]
            return r_parts > c_parts
        except ValueError:
            return remote > current # Fallback to string comparison
                    self.check_finished.emit(False, APP_VERSION, "")
            else:
                 self.check_finished.emit(False, "", "")
        except Exception as e:
            logging.debug(f"Update check failed: {e}")
            self.check_finished.emit(False, "", "")
        except Exception as e:
            logging.debug(f"Update check failed: {e}")
