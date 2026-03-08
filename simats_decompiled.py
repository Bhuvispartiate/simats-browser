# Decompiled from simats.exe (Python 3.12, PyInstaller)
# Original filename: simats.py
# SIMATS Browser Version 4.0

from PySide6.QtCore import QUrl, Qt, QTimer
from PySide6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PySide6.QtWebEngineCore import QWebEnginePage as _QWEPage
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLineEdit, QStatusBar,
    QMenu, QMenuBar, QProgressBar, QMessageBox, QDialog, QTextEdit,
    QSizePolicy, QPushButton
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
import sys
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
from PySide6.QtGui import QIcon
import os


class BrowserTab(QWebEngineView):
    def __init__(self, profile):
        super().__init__()

        icon_path = os.path.join(os.path.dirname(__file__), 'appicon.png')
        self.setWindowIcon(QIcon(icon_path))

        self._page_obj = QWebEnginePage(profile, self)
        self.setPage(self._page_obj)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.loadStarted.connect(self.on_load_started)
        self.loadFinished.connect(self.on_load_finished)

    def createWindow(self, _type):
        new_tab = BrowserTab(main_window.profile)
        main_window.add_new_tab(new_tab, "New Tab")
        return new_tab

    def on_load_started(self):
        main_window.progress.setRange(0, 0)
        main_window.status_bar.show()

    def on_load_finished(self, success):
        main_window.progress.setRange(0, 100)
        main_window.progress.setValue(100)
        if success:
            main_window.add_to_history(self.url().toString(), datetime.now())
            # Re-inject copy/paste unlock if enabled
            if hasattr(main_window, '_cp_enabled') and main_window._cp_enabled:
                main_window._inject_cp_js()
            # Re-inject always active if enabled
            if hasattr(main_window, '_active_enabled') and main_window._active_enabled:
                main_window._inject_active_js()
        main_window.status_bar.hide()


class ExamBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SIMATS Browser")
        self.setGeometry(100, 100, 1200, 800)

        # User data directory
        user_data_dir = Path.home() / ".simats_browser"
        user_data_dir.mkdir(exist_ok=True)

        # Database setup
        try:
            self.conn = sqlite3.connect(user_data_dir / "history.db")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", str(e))
            sys.exit(1)

        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS history (url TEXT, timestamp TEXT)")
        self.conn.commit()

        # Browser profile
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)

        # Browser widget
        self.browser = BrowserTab(self.profile)
        self.setCentralWidget(self.browser)

        self.browser.urlChanged.connect(self.update_url_bar)

        # Toolbar
        self.toolbar = self.addToolBar("Navigation")

        # Home button
        self.home_button = QPushButton("Home")
        self.home_button.setFixedSize(100, 30)
        self.home_button.clicked.connect(self.navigate_home)
        self.toolbar.addWidget(self.home_button)

        # Reload button
        self.reload_button = QPushButton("Reload")
        self.reload_button.setFixedSize(100, 30)
        self.reload_button.clicked.connect(self.reload_page)
        self.toolbar.addWidget(self.reload_button)

        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setFont(QFont("Arial", 16))
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_bar)

        # Go button
        self.go_button = QPushButton("Go")
        self.go_button.setFixedSize(100, 30)
        self.go_button.clicked.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.go_button)

        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setFixedSize(100, 30)
        self.clear_button.clicked.connect(self.clear_url)
        self.toolbar.addWidget(self.clear_button)

        # Menu bar
        menubar = QMenuBar()
        menubar.setStyleSheet("background-color: blue; color: white;")
        self.setMenuBar(menubar)

        # File menu
        file_menu = QMenu("File", self)
        menubar.addMenu(file_menu)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        file_menu.addAction(about_action)

        history_action = QAction("History", self)
        history_action.triggered.connect(self.show_history)
        file_menu.addAction(history_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Status bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        # Progress bar
        self.progress = QProgressBar(self)
        self.progress.setTextVisible(True)
        self.progress.setFormat("Loading: %p%")
        self.status_bar.addPermanentWidget(self.progress)
        self.status_bar.hide()

        # Navigate to home
        self.browser.setUrl(QUrl("https://www.google.com"))

        # Cleanup old history
        self.cleanup_history()

        # --- Hidden extensions (no UI, shortcut-activated only) ---
        self._cp_enabled = False
        self._aot_enabled = False
        self._active_enabled = False

        # Ctrl+Shift+C  →  Toggle copy/paste + select unlock
        _s1 = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        _s1.activated.connect(self._toggle_cp)

        # Ctrl+Shift+T  →  Toggle always-on-top
        _s2 = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        _s2.activated.connect(self._toggle_aot)

        # Ctrl+Shift+A  →  Toggle always-active window
        _s3 = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        _s3.activated.connect(self._toggle_active)

    # ---- Hidden: Copy/Paste + Select All unlock ----
    def _toggle_cp(self):
        self._cp_enabled = not self._cp_enabled
        if self._cp_enabled:
            self._inject_cp_js()
        else:
            self._remove_cp_js()
        self._flash("\u2713 (Copy/Paste)" if self._cp_enabled else "\u2717 (Copy/Paste)")

    def _inject_cp_js(self):
        js = r"""
        (function(){
            if(window.__allowCopyInjected) return;
            window.__allowCopyInjected = true;

            // ===== 1. Force-enable CSS selection everywhere =====
            var style = document.createElement('style');
            style.id = '__allow_copy_style';
            style.textContent = [
                '*, *::before, *::after {',
                '  -webkit-user-select: auto !important;',
                '  -moz-user-select: auto !important;',
                '  -ms-user-select: auto !important;',
                '  user-select: auto !important;',
                '  -webkit-touch-callout: default !important;',
                '}',
            ].join('\n');
            (document.head || document.documentElement).appendChild(style);

            // ===== 2. Capture-phase: ONLY clipboard/select events =====
            // DO NOT intercept keydown/mousedown - breaks typing and dropdowns!
            ['copy','cut','paste','selectstart','contextmenu','dragstart','drop'].forEach(function(evt){
                document.addEventListener(evt, function(e){
                    e.stopImmediatePropagation();
                    return true;
                }, true);
            });

            // ===== 3. Nuke inline event handlers =====
            function cleanElement(el) {
                el.oncopy = null;
                el.oncut = null;
                el.onpaste = null;
                el.oncontextmenu = null;
                el.onselectstart = null;
                el.ondragstart = null;
                el.ondrop = null;
                var attrs = ['oncopy','oncut','onpaste','oncontextmenu',
                             'onselectstart','ondragstart','ondrop'];
                attrs.forEach(function(a){
                    if(el.hasAttribute && el.hasAttribute(a)) el.removeAttribute(a);
                });
                if(el.style){
                    el.style.setProperty('user-select', 'auto', 'important');
                    el.style.setProperty('-webkit-user-select', 'auto', 'important');
                }
            }
            cleanElement(document);
            if(document.body) cleanElement(document.body);
            document.querySelectorAll('*').forEach(cleanElement);

            // ===== 4. MutationObserver for dynamic content =====
            var observer = new MutationObserver(function(mutations){
                mutations.forEach(function(m){
                    m.addedNodes.forEach(function(node){
                        if(node.nodeType === 1){
                            cleanElement(node);
                            if(node.querySelectorAll) node.querySelectorAll('*').forEach(cleanElement);
                        }
                    });
                });
            });
            observer.observe(document.documentElement, {
                childList: true, subtree: true
            });

            // ===== 5. Override addEventListener: block clipboard blockers =====
            var _origAdd = EventTarget.prototype.addEventListener;
            EventTarget.prototype.addEventListener = function(type, fn, opts){
                var blocked = ['copy','cut','paste','selectstart','contextmenu','dragstart','drop'];
                if(blocked.indexOf(type) !== -1){
                    return; // silently swallow
                }
                return _origAdd.call(this, type, fn, opts);
            };

            // ===== 6. Lock document event handler setters =====
            ['oncontextmenu','onselectstart','oncopy','oncut','onpaste','ondragstart','ondrop'].forEach(function(prop){
                try {
                    Object.defineProperty(document, prop, {
                        get: function(){ return null; },
                        set: function(){ },
                        configurable: true
                    });
                } catch(e){}
            });

            // ===== 7. Protect getSelection =====
            var _origGetSel = window.getSelection;
            Object.defineProperty(window, 'getSelection', {
                get: function(){ return _origGetSel; },
                set: function(){ },
                configurable: true
            });

            // ===== 8. jQuery: unbind clipboard events =====
            if(window.jQuery || window.$){
                try {
                    var jq = window.jQuery || window.$;
                    jq('.bodytag').off('copy paste cut contextmenu dragstart drop');
                    jq('.bodytag').unbind('copy paste cut contextmenu dragstart drop');
                    jq(document).off('dragover drop');
                    jq(document).unbind('dragover drop');
                } catch(e){}
            }

            // ===== 9. CodeMirror: re-enable copy/paste/cut =====
            try {
                var cmElements = document.querySelectorAll('.CodeMirror');
                cmElements.forEach(function(cmEl){
                    var cm = cmEl.CodeMirror;
                    if(cm){
                        // Re-enable keyboard shortcuts blocked by extraKeys
                        var keys = cm.getOption('extraKeys') || {};
                        delete keys['Ctrl-X'];
                        delete keys['Ctrl-C'];
                        delete keys['Ctrl-V'];
                        delete keys['Cmd-X'];
                        delete keys['Cmd-C'];
                        delete keys['Cmd-V'];
                        cm.setOption('extraKeys', keys);
                        // Remove paste/cut/copy event handlers
                        cm.off('paste');
                        cm.off('cut');
                        cm.off('copy');
                    }
                });
            } catch(e){}

            console.log('[Allow Copy] Active - all protections bypassed');
        })();
        """
        self.browser._page_obj.runJavaScript(js)

    def _remove_cp_js(self):
        js = r"""
        (function(){
            // Only remove if we injected it
            if(!window.__allowCopyInjected) return;
            window.__allowCopyInjected = false;

            // 1. Remove forced CSS style
            var style = document.getElementById('__allow_copy_style');
            if(style) style.remove();

            // 2. We can't easily undo the EventTarget.prototype override since we don't 
            // store the original in a safe place for ALL pages, but we can stop blocking 
            // by setting a flag in window.
            
            // To be truly clean, we should reload the page
            window.location.reload();
        })();
        """
        self.browser._page_obj.runJavaScript(js)

    # ---- Hidden: Always-active window ----
    def _toggle_active(self):
        self._active_enabled = not self._active_enabled
        if self._active_enabled:
            self._inject_active_js()
        self._flash("\u2713 (Active)" if self._active_enabled else "\u2717 (Active)")

    def _inject_active_js(self):
        js = r"""
        (function(){
            if(window.__alwaysActiveInjected) return;
            window.__alwaysActiveInjected = true;

            // 1. Overwrite visibility properties
            ['hidden', 'mozHidden', 'webkitHidden'].forEach(function(prop) {
                try {
                    Object.defineProperty(document, prop, {
                        get: function() { return false; },
                        configurable: true
                    });
                } catch(e) {}
            });

            ['visibilityState', 'webkitVisibilityState'].forEach(function(prop) {
                try {
                    Object.defineProperty(document, prop, {
                        get: function() { return 'visible'; },
                        configurable: true
                    });
                } catch(e) {}
            });

            // 2. Block tracking events (capture phase)
            var blockedEvents = [
                'visibilitychange',
                'webkitvisibilitychange',
                'mozvisibilitychange',
                'blur',
                'mouseleave',
                'pagehide',
                'focusout'
            ];

            blockedEvents.forEach(function(evt) {
                window.addEventListener(evt, function(e) { e.stopImmediatePropagation(); }, true);
                document.addEventListener(evt, function(e) { e.stopImmediatePropagation(); }, true);
            });

            // 3. Prevent overriding methods like addEventListener for these events
            var _origAdd = EventTarget.prototype.addEventListener;
            EventTarget.prototype.addEventListener = function(type, fn, opts) {
                if (blockedEvents.indexOf(type) !== -1) {
                    return; // silently swallow
                }
                return _origAdd.call(this, type, fn, opts);
            };

            // 4. Override document hasFocus
            try {
                document.hasFocus = function() { return true; };
            } catch(e) {}

            console.log('[Always Active] Active - all visibility/focus protections bypassed');
        })();
        """
        self.browser._page_obj.runJavaScript(js)

    # ---- Hidden: Always-on-top ----
    def _toggle_aot(self):
        self._aot_enabled = not self._aot_enabled
        flags = self.windowFlags()
        if self._aot_enabled:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()  # Required after setWindowFlags
        self._flash("\u2713" if self._aot_enabled else "\u2717")

    # ---- Minimal status flash (2s) ----
    def _flash(self, symbol):
        self.status_bar.showMessage(symbol, 2000)
        self.status_bar.show()
        QTimer.singleShot(2000, lambda: self.status_bar.hide() if not self.progress.isVisible() else None)

    # ---- Original methods ----
    def add_to_history(self, url, timestamp):
        timestamp_str = timestamp.isoformat()
        self.cursor.execute("INSERT INTO history (url, timestamp) VALUES (?, ?)", (url, timestamp_str))
        self.conn.commit()
        self.cleanup_history()

    def cleanup_history(self):
        thirty_days_ago = datetime.now() - timedelta(days=30)
        self.cursor.execute("DELETE FROM history WHERE timestamp < ?", (thirty_days_ago.isoformat(),))
        self.conn.commit()

    def navigate_home(self):
        self.browser.setUrl(QUrl("https://www.google.com"))

    def reload_page(self):
        self.browser.reload()

    def navigate_to_url(self):
        qurl = QUrl(self.url_bar.text())
        if qurl.scheme() == "":
            qurl.setScheme("http")
        self.browser.setUrl(qurl)

    def clear_url(self):
        self.url_bar.clear()

    def update_url_bar(self, q):
        self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0)

    def show_history(self):
        history_dialog = QDialog(self)
        history_dialog.setWindowTitle("History")
        history_dialog.setFixedSize(800, 400)
        layout = QVBoxLayout()

        # History text display
        history_text = QTextEdit()
        history_text.setReadOnly(True)
        history_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        history_text.setTextInteractionFlags(Qt.NoTextInteraction)

        # Fetch history
        self.cursor.execute("SELECT url, timestamp FROM history ORDER BY timestamp DESC")
        history_content = ""
        for url, timestamp_str in self.cursor.fetchall():
            timestamp = datetime.fromisoformat(timestamp_str)
            history_content += f"{url} - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"

        history_text.setPlainText(history_content)
        layout.addWidget(history_text)
        history_dialog.setLayout(layout)
        history_dialog.exec()

    def show_about(self):
        about_message = "SIMATS Browser\n Version 4.0"
        about_dialog = QMessageBox(self)
        about_dialog.setWindowTitle("About")
        about_dialog.setFixedSize(400, 200)
        about_dialog.setText(about_message)
        about_dialog.setStandardButtons(QMessageBox.Ok)
        about_dialog.exec()

    def closeEvent(self, event):
        self.conn.close()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon_path = os.path.join(os.path.dirname(__file__), "titleicon.jpeg")
    app.setWindowIcon(QIcon(icon_path))
    main_window = ExamBrowser()
    main_window.show()
    sys.exit(app.exec())