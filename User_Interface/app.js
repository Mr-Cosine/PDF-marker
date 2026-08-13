//app.js
(function() {
    let fileItems = [];

    const selectOutputDir = document.getElementById('selectOutputDirBtn');
    const outputDirInput = document.getElementById('outputDirInput');
    const outputNameInput = document.getElementById('outputNameInput')
    const fileInput = document.getElementById('fileInput');
    const fileListEl = document.getElementById('fileList');
    const fileCountEl = document.getElementById('fileCount');
    const keywordInput = document.getElementById('keywordInput');
    const leniencyInput = document.getElementById('leniencyInput')
    const capitalToggle = document.getElementById('capitalToggle')
    const modelSelect = document.getElementById('modelSelect')
    const markBtn = document.getElementById('markBtn');
    const statusText = document.getElementById('statusText');
    const statusBar = document.getElementById('statusBar');



    function renderFileList() {
        fileListEl.innerHTML = '';

        fileItems = fileItems.filter(item => !(item.refcode === undefined && item.refcode === null));
        if (fileItems.length === 0) {
            const empty = document.createElement('li');
            empty.className = 'empty-message';
            empty.textContent = 'No files';
            fileListEl.appendChild(empty);
            updateMarkButton();
            return;
        }

        fileItems.forEach((item, index) => {
            const li = document.createElement('li');
            li.setAttribute("class", "file-list")

            const nameSpan = document.createElement('span');
            nameSpan.setAttribute("class", 'file-name');
            nameSpan.textContent = `${item.name}`;
            li.appendChild(nameSpan);

            const actionBtns = document.createElement('div');
            actionBtns.className = 'file-actions';

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
            actionBtns.appendChild(upBtn);

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
            actionBtns.appendChild(downBtn);

            const delBtn = document.createElement('button');
            delBtn.setAttribute('class', 'del-button')
            delBtn.textContent = '✖';
            delBtn.title = 'delete';   
            delBtn.refcode = item.refcode;
            delBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                fileItems = fileItems.filter(item => !(item.refcode === delBtn.refcode));
                renderFileList();
            })
            actionBtns.appendChild(delBtn);

            li.appendChild(actionBtns);
            fileListEl.appendChild(li);
        });
        
        updateMarkButton();
    }

    selectOutputDir.addEventListener('click', async () => {
        const result = await window.electronAPI.openDirDialog();
        outputDirInput.value = result || '';
        renderFileList();
    });

    // ----- File selection -----
    fileInput.addEventListener('click', async () => {
        const paths = await window.electronAPI.openPDFDialog();
        if (paths.length === 0) return;

        paths.forEach((filePath, index) => {
            const name = filePath.split(/[\\/]/).pop();
            fileItems.push({
                name: name,
                path: filePath,
                refcode: crypto.randomUUID()
            });
        });
        renderFileList();
    });

    function updateMarkButton() {
        const model = modelSelect.value;
        const outputDir = outputDirInput.value.trim();
        const outputName = outputNameInput.value.trim();
        const leniency = parseFloat(leniencyInput.value);
        const hasFiles = fileItems.length > 0;
        markBtn.disabled = !(outputDir && outputName && hasFiles && !isNaN(leniency));
    }

    document.getElementById('keywordInput').addEventListener('input', updateMarkButton);
    document.getElementById('outputNameInput').addEventListener('change', updateMarkButton);

    // ----- Mark button -----
    markBtn.addEventListener('click', async () => {
        const model = modelSelect.value;
        const keyword = keywordInput.value.trim();
        const capital = capitalToggle.checked;
        const outputDir = outputDirInput.value.trim();
        const outputName = outputNameInput.value.trim();
        const leniency = parseFloat(leniencyInput.value)

        const files = fileItems.map((item, index) => ({
            index: index,
            path: item.path
        }));

        const settings = { model, keyword, capital, files, leniency, outputDir, outputName };

        markBtn.disabled = true
        const ogMarkBtnText = markBtn.textContent
        markBtn.textContent = "标注中 Annotating..."
        statusBar.classList.remove('hidden');

        try {
            window.electronAPI.stopUpdateProgress?.()
            window.electronAPI.updateProgress((message) => {
                statusBar.textContent = message;
            });

            await window.electronAPI.markPDF(settings); 
        } 
        finally {
            markBtn.disabled = false;
            markBtn.textContent = ogMarkBtnText;
            statusBar.textContent = '';
            statusBar.classList.add('hidden');
        }
    });

    renderFileList();
})();