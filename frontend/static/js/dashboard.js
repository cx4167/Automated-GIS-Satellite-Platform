// Update data inventory
async function updateDataInventory() {
    try {
        const response = await fetch('/api/data-inventory');
        const data = await response.json();
        
        // Local Files
        const filesContainer = document.getElementById('local-files-inventory');
        if (data.local_files.length === 0) {
            filesContainer.innerHTML = '<p class="loading">No files stored yet</p>';
        } else {
            let filesHtml = '';
            const totalSize = (data.total_size / (1024 * 1024)).toFixed(2);
            filesHtml += `<p><strong>Total Size: ${totalSize} MB</strong></p>`;
            
            data.local_files.forEach(file => {
                const size = (file.size / 1024).toFixed(2);
                filesHtml += `
                    <div class="inventory-item">
                        <h4>${file.path}</h4>
                        <p>Size: ${size} KB | Modified: ${new Date(file.modified).toLocaleString()}</p>
                    </div>
                `;
            });
            filesContainer.innerHTML = filesHtml;
        }
        
        // PostGIS Tables (same as before)
        // ...
        
    } catch (error) {
        console.error('Error updating inventory:', error);
    }
}
