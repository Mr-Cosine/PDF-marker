const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

app.whenReady().then(() => {
    function createWindow() {
        const win = new BrowserWindow({
            width: 960,
            height: 720,
            fullscreenable: false,
            resizable: false,
            webPreferences: {
                preload: path.join(__dirname, 'preload.js'),
                contextIsolation: true,
                nodeIntegration: false,
            }
        });
        win.loadFile('frontend/UI.html');
    }

    createWindow();
    app.on('activate', () => {if (BrowserWindow.getAllWindows().length === 0) createWindow();});
});
app.on('window-all-closed', () => {if (process.platform !== 'darwin') app.quit();});

ipcMain.handle('open-pdf-dialog', async () => {
    const result = await dialog.showOpenDialog({
        properties: ['openFile', 'multiSelections'],
        filters: [
            { name: 'PDF 文件', extensions: ['pdf'] }
        ]
    });
    return result.canceled ? [] : result.filePaths;
});

ipcMain.handle('open-dir-dialog', async () => {
    const result = await dialog.showOpenDialog({
        properties: ['openDirectory']
    });
    return result.canceled ? [] : result.filePaths;
});

ipcMain.handle('mark-pdf', async (event, settings) => {
    const scriptPath = path.join(__dirname, 'PDFmarker.py');
    
    // 检查脚本是否存在
    if (!fs.existsSync(scriptPath)) throw new Error(`Python 脚本不存在: ${scriptPath}`);

    // 使用 'py' 或 'python'，根据 Windows 调整
    const pythonCmd = process.platform === 'win32' ? 'py' : 'python3';

    const pythonProcess = spawn(pythonCmd, [scriptPath]);

    // 写入 JSON 数据
    pythonProcess.stdin.write(JSON.stringify(settings));
    pythonProcess.stdin.end();

    let outputData = '';
    let errorData = '';

    pythonProcess.stdout.on('data', (data) => {
        outputData += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        errorData += data.toString();
        console.error(`[Python stderr] ${data}`);
    });

    // 返回一个 Promise，等待进程结束
    return new Promise((resolve, reject) => {
        pythonProcess.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(`Python 退出码 ${code}\n错误详情: ${errorData}`));
            } else {
                try {
                    const result = JSON.parse(outputData);
                    resolve(result);
                } catch (e) {
                    reject(new Error(`解析 JSON 失败: ${outputData}`));
                }
            }
        });

        // 超时保护（可选）
        const timeout = setTimeout(() => {
            pythonProcess.kill();
            reject(new Error('Python 处理超时（5分钟）'));
        }, 300000);
        pythonProcess.on('exit', () => clearTimeout(timeout));
    });
});