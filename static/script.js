const form = document.getElementById('plantForm');
        const body = document.body;
        const loading = document.getElementById('loading');
        const errorDiv = document.getElementById('error');
        const dropZone = document.getElementById('drop-zone');
        const imageInput = document.getElementById('image-input');
        const fileNameDisplay = document.getElementById('file-name-display');
        const resultImagesContainer = document.getElementById('result-images');
        dropZone.addEventListener('click', () => {
            imageInput.click();
        });
        imageInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                fileNameDisplay.textContent = `Archivo seleccionado: ${file.name}`;
            } else {
                fileNameDisplay.textContent = '';
            }
        });
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });
        function preventDefaults (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
        });
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
        });
        dropZone.addEventListener('drop', handleDrop, false);
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                imageInput.files = files;
                fileNameDisplay.textContent = `Archivo seleccionado: ${files[0].name}`;
            } else {
                fileNameDisplay.textContent = '';
            }
        }
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            body.classList.remove('results-active');
            loading.classList.remove('hidden');
            errorDiv.classList.add('hidden');
            const formData = new FormData(form);
            resultImagesContainer.innerHTML = ''; 
            try {
                const res = await fetch('/identificar_ia', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                loading.classList.add('hidden');
                if (!res.ok) {
                    throw new Error(data.error || 'No se encontraron coincidencias.');
                }
                document.getElementById('scientificName').textContent = data.scientificName || 'No disponible';
                document.getElementById('authorship').textContent = data.authorship || 'No disponible';
                document.getElementById('commonNames').textContent = (data.commonNames && data.commonNames.length > 0) ? data.commonNames.join(', ') : 'No disponible';
                document.getElementById('genus').textContent = data.genus || 'No disponible';
                document.getElementById('family').textContent = data.family || 'No disponible';
                document.getElementById('score').textContent = data.score ? parseFloat(data.score).toFixed(2) : 'N/A';

                if (data.imageUrls && data.imageUrls.length > 0) {
                    data.imageUrls.forEach(url => {
                        console.log("URL de imagen recibida:", url);
                        const img = document.createElement('img');
                        img.src = url;
                        img.alt = data.scientificName || 'Imagen de planta';
                        img.classList.add('w-50', 'h-50', 'object-cover', 'rounded-lg', 'shadow-md'); 
                        resultImagesContainer.appendChild(img);
                    });
                } else {
                    resultImagesContainer.innerHTML = '<p class="text-sm text-gray-500">No se encontraron imágenes relacionadas.</p>';
                }
                

                body.classList.add('results-active');
            } catch (err) {
                loading.classList.add('hidden');
                errorDiv.textContent = err.message;
                errorDiv.classList.remove('hidden');
                body.classList.remove('results-active');
            }
        });