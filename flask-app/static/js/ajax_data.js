document.getElementById("indexForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const path = document.getElementById("path").value;
    const recursive = document.getElementById("recursive").checked;
    const replaceFilename = document.getElementById("replace_filename").checked;

    fetch("/indexing", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            path: path,
            recursive: recursive,
            replace_filename: replaceFilename
        })
    })
    .then(res => res.json())
    .then(data => {
        showPopup(`Indexed ${data.indexed_count} file(s).`);
    })
    .catch(() => showPopup("Indexing failed!"));
});

document.getElementById("searchForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const query = document.getElementById("searchInput").value;
    fetch(`/search?query=${encodeURIComponent(query)}`)
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showPopup(data.error);
        } else {
            displaySearchResults(data.results);
        }
    })
    .catch(() => showPopup("Search failed!"));
});

function displaySearchResults(results) {
    const container = document.getElementById("searchResults") || document.createElement("div");
    container.id = "searchResults";
    container.innerHTML = `
        <h2>Search Results</h2>
        <table>
            <tr>
                <th>Path</th>
                <th>Page</th>
                <th>Match count</th>
                <th>Total TF</th>
                <th>Terms matched</th>
                <th>Snippets</th>
            </tr>
            ${results.map(row => `
                <tr>
                    <td>${row[0]}</td>
                    <td>${row[1]}</td>
                    <td>${row[2]}</td>
                    <td>${row[3]}</td>
                    <td><ul>${row[4].map(t => `<li>${t}</li>`).join('')}</ul></td>
                    <td><ul>${row[5].map(s => `<li>${s}</li>`).join('')}</ul></td>
                </tr>
            `).join('')}
        </table>
    `;
    document.body.appendChild(container);
}
