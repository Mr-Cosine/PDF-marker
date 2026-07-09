(function() {
    // ----- 状态 -----
    let fileItems = []; // 存储 { name, file } 对象

    // DOM 引用
    const selectOutputDir = document.getElementById('selectOutputDirBtn');
    const outputDirInput = document.getElementById('outputDirInput');
    const fileInput = document.getElementById('fileInput');
    const fileListEl = document.getElementById('fileList');
    const fileCountEl = document.getElementById('fileCount');
    const keywordInput = document.getElementById('keywordInput');
    const vagueToggle = document.getElementById('vagueToggle');
    const markBtn = document.getElementById('markBtn');

    // ----- 渲染列表 -----
    function renderFileList() {
        // 清空
        fileListEl.innerHTML = '';

        if (fileItems.length === 0) {
            const empty = document.createElement('li');
            empty.className = 'empty-message';
            empty.textContent = 'No files';
            fileListEl.appendChild(empty);
            markBtn.disabled = true;
            return;
        }

        markBtn.disabled = false;

        fileItems.forEach((item, index) => {
            const li = document.createElement('li');
            li.setAttribute("class", "file-list")

            // 文件名 + 大小信息
            const nameSpan = document.createElement('span');
            nameSpan.setAttribute("class", 'file-name');
            nameSpan.textContent = `${item.name}`;
            li.appendChild(nameSpan);

            // 操作按钮组
            const actions = document.createElement('div');
            actions.className = 'file-actions';

            // 上移
            const upBtn = document.createElement('button');
            upBtn.setAttribute('class', 'action-button')
            upBtn.textContent = '▲';
            upBtn.title = 'up';
            upBtn.disabled = index === 0;
            upBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (index > 0) {
                    [fileItems[index], fileItems[index - 1]] = [fileItems[index - 1], fileItems[index]];
                    renderFileList();
                }
            });
            actions.appendChild(upBtn);

            // 下移
            const downBtn = document.createElement('button');
            downBtn.setAttribute('class', 'action-button')
            downBtn.textContent = '▼';
            downBtn.title = 'down';
            downBtn.disabled = index === fileItems.length - 1;
            downBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (index < fileItems.length - 1) {
                    [fileItems[index], fileItems[index + 1]] = [fileItems[index + 1], fileItems[index]];
                    renderFileList();
                }
            });
            actions.appendChild(downBtn);

            const delBtn = document.createElement('button');
            delBtn.setAttribute('class', 'del-button')
            delBtn.textContent = '✖';
            delBtn.title = 'delete';   
            delBtn.refcode = item.path;
            delBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                fileItems = fileItems.filter(item => item.path !== delBtn.refcode);
                renderFileList();
            })
            actions.appendChild(delBtn);

            li.appendChild(actions);
            fileListEl.appendChild(li);
        });
    }

    selectOutputDir.addEventListener('click', async () => {
        const result = await window.electronAPI.openDirDialog();
        outputDirInput.value = result || '';
    });

    // ----- File selection -----
    fileInput.addEventListener('click', async () => {
        const paths = await window.electronAPI.openPDFDialog();
        if (paths.length === 0) return;

        // 将路径添加到文件列表
        paths.forEach((filePath, index) => {
            // 从路径中提取文件名
            const name = filePath.split(/[\\/]/).pop();
            fileItems.push({
                name: name,
                path: filePath,
            });
        });
        renderFileList();
    });

    // ----- Mark button -----
    document.getElementById('markBtn').addEventListener('click', async () => {
        const keyword = document.getElementById('keywordInput').value.trim() || 'NEW VAM';
        const vague = document.getElementById('vagueToggle').checked;
        const outputDir = document.getElementById('outputDirInput').value.trim() || '';
        const outputName = document.getElementById('outputNameInput').value.trim() || 'MarkedPDF';


        const files = fileItems.map((item, index) => ({
            index: index,
            path: item.path
        }));

        const settings = { keyword, vague, files, outputDir, outputName };
        const result = await window.electronAPI.markPDF(settings);
        alert(result.message);
    });

    renderFileList();
})();