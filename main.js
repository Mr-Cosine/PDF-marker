// main.js
const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const readline = require('readline');

const ASPECT_RATIO = 4/3;
const WINDOW_HEIGHT = 810;
const WINDOW_WIDTH = WINDOW_HEIGHT*ASPECT_RATIO;

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
    const getExePath = () => {
        if (!app.isPackaged) return path.join(__dirname, 'PDFmarkerApp', 'PDFmarkerExecutable', 'PDFmarkerExecutable.exe')
        return path.join(process.resourcesPath, 'PDFmarkerApp', 'PDFmarkerExecutable', 'PDFmarkerExecutable.exe');
    };

    const exePath = getExePath();

    if (!fs.existsSync(exePath)) {
        const msg = `.exe file don't exist at: ${exePath}`;
        dialog.showErrorBox('文件缺失', msg);
        throw new Error(msg);
    }

    try {
        const { execFile } = require('child_process');
        const marker = execFile(exePath);

        marker.stdin.write(JSON.stringify(settings));
        marker.stdin.end();

        let outputData = '';
        let logData = [
            '[SETTINGS]',
            `- Files: \n${settings.files.map(f => "    · " + f.path).join(',\n')}`,
            `- Keyword: ${settings.keyword}`,
            `- Output directory: ${settings.outputDir}`,
            `- Output file name: ${settings.outputName}`,
            `- Match Capital: ${settings.capital}`,
            `- OCR model: ${settings.model}`,
            `- Parsing leniency: ${settings.leniency}`,
            `- Resolution of OCR (dpi): ${settings.DPI}`,
            '===================================',
            '[EXECUTION LOG]\n'].join('\n');

        const outcome_listener = readline.createInterface({ input: marker.stdout, terminal: false });
        outcome_listener.on('line', (line) => {
            outputData = line.toString();
        })

        const runtime_listener = readline.createInterface({ input: marker.stderr, terminal: false });
        runtime_listener.on('line', (line) => {
            try {
                const message = JSON.parse(line);

                if (message.type === "print") {
                    logData += message.content.toString() + "\n";
                    console.log(message.content.toString())
                }
                else if (message.type === "report") {
                    event.sender.send('update-progress', { message: message.content.toString() });
                }
                else {
                    logData += message.content.toString();
                }
            } 
            catch (e) {
                logData += line + " [JSON parsing failed]\n";
            }
        });

        return new Promise((resolve, reject) => {
            marker.on('close', async (code) => {
                if (code !== 0) {
                    const errorMsg = `Process quit, code: ${code}\n${logData}`;
                    dialog.showErrorBox('Execution failed', errorMsg);
                    reject(new Error(errorMsg));
                } else {
                    let result = null
                    try {result = JSON.parse(outputData);
                    } catch (e) {
                        const error = `JSON parsing failed, original string: ${outputData}`;
                        dialog.showErrorBox('Parsing error', error);
                        reject(new Error(error));
                    }
                    if (result.success === true) {
                        logData += '\n ☑ Successful run ☑';
                        dialog.showMessageBox({
                            type: 'info',
                            title: 'Execution log',
                            message: logData
                        });
                    } else {
                        logData += `Error: ${result.message}`
                        logData += '\n ⚠ Break after error happens ⚠';
                        await Promise.all([
                            dialog.showMessageBox({
                                type: 'info',
                                title: 'Execution log',
                                message: logData
                            }),
                            dialog.showMessageBox({
                                type: 'warning',
                                title: 'DEBUG INFO',
                                message: result.message,
                                detail: result.details.join('\n'),
                                buttons: ['OK'],
                            })
                        ]);
                    }
                    resolve(result);
                }
            });

            marker.on('error', (err) => {
                dialog.showErrorBox('Execution failed', err.message);
                reject(err);
            });
        });
    } catch (e) {
        dialog.showErrorBox('Unexpected error', e.message);
        throw e;
    }
});