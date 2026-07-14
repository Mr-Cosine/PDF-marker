(function() {
    let fileItems = [];

    const selectOutputDir = document.getElementById('selectOutputDirBtn');
    const outputDirInput = document.getElementById('outputDirInput');
    const fileInput = document.getElementById('fileInput');
    const fileListEl = document.getElementById('fileList');
    const fileCountEl = document.getElementById('fileCount');
    const keywordInput = document.getElementById('keywordInput');
    const vagueToggle = document.getElementById('vagueToggle');
    const markBtn = document.getElementById('markBtn');

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
        const keyword = document.getElementById('keywordInput').value.trim();
        const outputDir = document.getElementById('outputDirInput').value.trim();
        const outputName = document.getElementById('outputNameInput').value.trim();
        const hasFiles = fileItems.length > 0;
        markBtn.disabled = !(keyword && outputDir && outputName && hasFiles);
    }

    document.getElementById('keywordInput').addEventListener('input', updateMarkButton);
    document.getElementById('outputNameInput').addEventListener('change', updateMarkButton);

    // ----- Mark button -----
    markBtn.addEventListener('click', async () => {
        const keyword = document.getElementById('keywordInput').value.trim();
        const vague = document.getElementById('vagueToggle').checked;
        const capital = document.getElementById('capitalToggle').checked;
        const outputDir = document.getElementById('outputDirInput').value.trim();
        const outputName = document.getElementById('outputNameInput').value.trim();

        const files = fileItems.map((item, index) => ({
            index: index,
            path: item.path
        }));

        const settings = { keyword, vague, capital, files, outputDir, outputName };
        const result = await window.electronAPI.markPDF(settings);
        alert(result.message);
    });

    renderFileList();
})();