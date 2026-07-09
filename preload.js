// preload.js
const { contextBridge, ipcRenderer } = require('electron');

// 暴露给渲染进程的安全 API
contextBridge.exposeInMainWorld('electronAPI', {
    /**
     * 打开系统对话框选择 PDF 文件（支持多选）
     * @returns {Promise<string[]>} 选中的文件路径数组
     */
    openPDFDialog: () => ipcRenderer.invoke('open-pdf-dialog'),

    /**
     * 打开系统对话框选择目录
     * @returns {Promise<string>} 选中的目录路径
     */
    openDirDialog: () => ipcRenderer.invoke('open-dir-dialog'),

    /**
     * 发送 PDF 标记请求给主进程
     * @param {Object} settings - 包含 keyword, vague, files 的对象
     * @returns {Promise<Object>} 处理结果
     */
    markPDF: (settings) => ipcRenderer.invoke('mark-pdf', settings)
});