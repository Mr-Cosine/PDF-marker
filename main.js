const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

const RATIO = 4/3;
const WINDOW_HEIGHT = 720;
const WINDOW_WIDTH = WINDOW_HEIGHT*RATIO;

const isDev = !app.isPackaged;

app.whenReady().then(() => {
    function createWindow() {
        const win = new BrowserWindow({
            width: WINDOW_WIDTH,
            height: WINDOW_HEIGHT,
            fullscreenable: false,
            resizable: false,
            webPreferences: {
                preload: path.join(__dirname, 'preload.js'),
                contextIsolation: true,
                nodeIntegration: false,
            }
        });
        win.loadFile(path.join(__dirname, 'frontend/UI.html'));
    }

    createWindow();
    app.on('activate', () => {if (BrowserWindow.getAllWindows().length === 0) createWindow();});
});
app.on('window-all-closed', () => {if (process.platform !== 'darwin') app.quit();});

ipcMain.handle('open-pdf-dialog', async () => {
    const result = await dialog.showOpenDialog({
        properties: ['openFile', 'multiSelections'],
        filters: [
            { name: 'PDF files', extensions: ['pdf'] }
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
    const scriptPath = path.join(isDev? __dirname : process.resourcesPath, 'PDFmarker.py');
    
    if (!fs.existsSync(scriptPath)) throw new Error(`Python script not exist: ${scriptPath}`);

    const pythonCmd = process.platform === 'win32' ? 'py' : 'python3';

    const pythonProcess = spawn(pythonCmd, [scriptPath]);

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

    return new Promise((resolve, reject) => {
        pythonProcess.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(`Python Exit Code ${code}\nTraceback: ${errorData}`));
            } else {
                try {
                    const result = JSON.parse(outputData);
                    resolve(result);
                } catch (e) {
                    reject(new Error(`JSON parsing failed: ${outputData}`));
                }
            }
        });
    });
});