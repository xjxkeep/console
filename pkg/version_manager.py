import requests
from pkg.model import Version
from PyQt5.QtCore import QThread,pyqtSignal,QProcess,QObject
from PyQt5.QtWidgets import QApplication
from pkg.api import API
import os, sys, json, hashlib, shutil, tempfile, zipfile
from pyshortcuts import make_shortcut
from qfluentwidgets import ProgressBar,MessageBox,Dialog

class DownloadTask(QThread):
    progress = pyqtSignal(int)        # 0-100
    finished = pyqtSignal(str, str)   # tmp_path, md5
    error    = pyqtSignal(str)

    def __init__(self, url,base_dir):
        super().__init__()
        self.url = url
        self.base_dir=base_dir
    def run(self):
        try:
            with requests.get(self.url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                fd, tmp_path = tempfile.mkstemp(suffix='.zip', dir=self.base_dir / "tmp")
                with os.fdopen(fd, 'wb') as f:
                    dl = 0
                    for chunk in r.iter_content(1024*64):
                        if not chunk:
                            continue
                        dl += len(chunk)
                        f.write(chunk)
                        self.progress.emit(int(dl / total * 100))
            self.finished.emit(tmp_path, "")
        except Exception as e:
            self.error.emit(str(e))

class UpdateTask(QThread):
    progress = pyqtSignal(int)        # 0-100
    finished = pyqtSignal(str, str)   # tmp_path, md5
    error    = pyqtSignal(str)
    
    def __init__(self,zip_path,md5):
        super().__init__()
        self.zip_path=zip_path
        self.md5=md5
    def _verify(self, path):
        if not self.md5:
            return True
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest() == self.md5

    def run(self):
        if not self._verify(self.zip_path):
            self.error.emit("文件校验失败")
            return
        with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
            zip_ref.extractall("./app")
        os.remove("./console")
        make_shortcut(script="./app/console",name="console")
        self.finished.emit(self.zip_path, self.md5)


class VersionManager(QObject):

    new_version_found=pyqtSignal(Version)
    update_finished=pyqtSignal(bool)
    update_error=pyqtSignal(str)
    
    download_finished = pyqtSignal(str, str)   # tmp_path, md5
    download_error    = pyqtSignal(str)
    progress=pyqtSignal(str,int)
    
    
    def __init__(self,setting:dict,api:API,parent:QObject=None):
        super().__init__(parent)
        self.dialog=Dialog("更新","检测到新版本，点击更新。",parent)
        self.progressToast=ProgressBar(parent=parent,useAni=True)
        self.setting=setting
        self.version_dir=setting.get("version_dir","assets/version")
        self.local_version=Version.model_validate_json(setting.get("version","{}"))
        self.remote_version=None
        self.api=api
    
    def check_update(self) -> bool:
        self.remote_version=self.api.check_version()
        if self.local_version.version ==None or self.remote_version.version!=self.local_version.version:
            self.new_version_found.emit(self.remote_version)
            if self.dialog.exec()==0:
                self.update()
            return True
        else:
            return False

    def update(self):
        url=self.remote_version.url
        self.task = DownloadTask(url,"./app")
        self.progressToast.setFormat("文件下载中: %p")
        self.task.progress.connect(self.progressToast.update)
        # self.task.progress.connect(self.download_progress)
        self.task.finished.connect(self._handle_download_finished)
        self.task.error.connect(self.download_error)
        self.task.start()
        
    def _handle_download_finished(self,tmp_path,md5):
        self.update_task = UpdateTask(tmp_path,md5)
        self.progressToast.setFormat("正在更新: %p")
        self.update_task.progress.connect(self.progressToast.update)
        self.update_task.finished.connect(self.update_finished)
        self.update_task.error.connect(self.update_error)
        self.update_task.start()
    
    def restart(self):
        QProcess.startDetached(sys.executable, [sys.argv[0]])
        QApplication.quit()