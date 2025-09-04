document.getElementById("indexForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const path = document.getElementById("path").value;
    const recursive = document.getElementById("recursive").checked;
    const replaceFilename = document.getElementById("replace_filename").checked;

    if (replaceFilename) {
        const confirmed = await showPopup("Are you sure you want to replace the FULL filename? This cannot be reverted!", true);
        if (!confirmed) {
            return;
        }
    }

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

    const query = document.getElementById("query").value;
    const fullText = document.getElementById("full_text").checked;

    callSearch(query, fullText);
});

function displaySearchResults(results) {
    const container = document.getElementById("searchResults") || document.createElement("div");
    container.id = "searchResults";
    container.innerHTML = `
        <h2>Search Results</h2>
        <table>
            <tr>
                <th>Path</th>
                <th>Pages</th>
                <th>Terms matched</th>
                <th>Snippets</th>
            </tr>
            ${results.map(row => `
                <tr>
                    <td>${row.path}</td>
                    <td>${row.page_numbers.join(", ")}</td>
                    <td><ul>${row.match_terms.map(t => `<li>${t}</li>`).join('')}</ul></td>
                    <td><ul>${row.snippet.map(s => `<li>${s}</li>`).join('')}</ul></td>
                </tr>
            `).join('')}
        </table>
    `;
    document.body.appendChild(container);
}

function callSearch(query, full_text) {
    fetch(`/search`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            query: query,
            full_text: full_text,
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showPopup(data.error);
        } else {
            displaySearchResults(data.results);
            if (data.spellchecked != query) {
                showDidYouMean(data.spellchecked);
            }
        }
    })
    .catch(err => {
        console.error("Fetch failed:", err);
        showPopup("Search failed!");
    });
}

function showDidYouMean(text) {
    document.getElementById('didYouMeanText').textContent = `Did you mean: ${text}`;
    document.getElementById('didYouMean').style.display = 'flex';
}

function closeDidYouMean() {
    const query = document.getElementById('didYouMeanText').textContent.split(":")[1].trim();
    callSearch(query)
    document.getElementById('didYouMean').style.display = 'none';
}