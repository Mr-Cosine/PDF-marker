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
        win.loadFile(path.join(__dirname, 'User_Interface/UI.html'));
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
    try {
        const scriptPath = path.join(isDev? __dirname: process.resourcesPath, 'PDFmarker.py');
        console.log('scriptPath:', scriptPath);
        console.log('exists?', fs.existsSync(scriptPath));
        if (!fs.existsSync(scriptPath)) {
            dialog.showErrorBox("File error", `Python script not found at ${scriptPath}`);
            throw(new Error(`Python script not found at ${scriptPath}`));
        }

        const pythonCmd = process.platform === 'win32' ? 'py' : 'python3';

        const pythonProcess = spawn(pythonCmd, [scriptPath]);

        pythonProcess.stdin.write(JSON.stringify(settings));
        pythonProcess.stdin.end();

        let outputData = '';
        let logData = [
            '[SETTINGS]',
            `   - Keyword: ${settings.keyword}`,
            `   - Vague Search: ${settings.vague}`,
            `   - Match Capital: ${settings.capital}`,
            `   - Files: ${settings.files.map(f => f.path).join(', ')}`,
            `   - Output directory: ${settings.outputDir}`,
            `   - Output file name: ${settings.outputName}`,
            '===================================',
            '[EXECUTION LOG]'
        ].join('\n');
        const startLog = logData;

        pythonProcess.stdout.on('data', (data) => {
            outputData += data.toString() + "\n";
        });

        pythonProcess.stderr.on('data', (data) => {
            logData += data.toString() + "\n";
        });

        return new Promise((resolve, reject) => {
            pythonProcess.on('close', (code) => {
                if (code !== 0) {
                    dialog.showErrorBox("Error in execution", `Python exited with code ${code}\n${logData}`);
                    reject(new Error(`Python exited with code ${code}\n${logData}`));
                } 
                else {
                    try {
                        const result = JSON.parse(outputData);
                        logData += "\nSuccessfully Done.";
                        dialog.showMessageBox({
                                type: 'info',
                                title: 'Success',
                                message: logData
                            })
                        resolve(result);
                    } catch (e) {
                        dialog.showErrorBox("Error in execution", `JSON parse error: ${outputData}`);
                        reject(new Error(`JSON parse error: ${outputData}`))
                    }
                }
            });
        });
    } catch (e) {
        dialog.showErrorBox('pdf-error', e);
    }
});