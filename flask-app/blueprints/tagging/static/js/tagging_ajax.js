document.getElementById("searchForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const query = document.getElementById("query").value;

    callSearch(query);
});

function displaySearchResults(results) {
    const container = document.getElementById("searchResults") || document.createElement("div");
    container.id = "searchResults";
    container.innerHTML = `
        <table>
            <tr>
                <th>Path</th>
                <th>Pages</th>
                <th>Terms matched</th>
                <th>Snippets</th>
                <th>Tags</th>
            </tr>
            ${results.map(row => `
                <tr>
                    <td>${row.path}</td>
                    <td>${row.page_numbers.join(", ")}</td>
                    <td><ul>${row.match_terms.map(t => `<li>${t}</li>`).join('')}</ul></td>
                    <td><ul>${row.snippet.map(s => `<li>${s}</li>`).join('')}</ul></td>
                    <td class="tagging-cell" data-path="${row.path}">Loading...</td>
                </tr>
            `).join('')}
        </table>
    `;

    document.querySelectorAll(".tagging-cell").forEach(cell => {
    const path = cell.dataset.path;

    fetch("/tagging/tags", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: path })
    })
    .then(res => {
        if (!res.ok) throw new Error(`Tagging failed for ${path}`);
        return res.json();
    })
    .then(data => {
        cell.textContent = data.tag || "(no tags)";
    })
    .catch(err => {
        console.error(err);
        cell.textContent = "Error";
    });
    });
    document.body.appendChild(container);
}

function callSearch(query) {
    fetch(`/search`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            query: query,
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