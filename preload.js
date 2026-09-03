// preload.js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    /**
     * Select Files using the system dialog
     * @returns {Promise<string[]>} # list of selected file path string
     */
    openPDFDialog: () => ipcRenderer.invoke('open-pdf-dialog'),

    /**
     * Seleect a directory using the system dialog
     * @returns {Promise<string>} # directory path string
     */
    openDirDialog: () => ipcRenderer.invoke('open-dir-dialog'),

    /**
     * Invoke the PDF marking process in the main process
     * @param {Object} settings
     * @returns {Promise<Object>} # result of the marking process: success info, log, error message
     */
    markPDF: (settings) => ipcRenderer.invoke('mark-pdf', settings),

    /**
     * refresh the progress bar in the UI
     * @param {Object} message # string of message
     */
    updateProgress: (callback) => {
        ipcRenderer.on('update-progress', (event, data) => {
            callback(data.message);
        });
    },
    stopUpdateProgress: () => {
        ipcRenderer.removeAllListeners('update-progress');
    }
});
