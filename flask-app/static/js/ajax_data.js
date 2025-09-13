document.getElementById("indexForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const path = document.getElementById("path").value;
    const recursive = document.getElementById("recursive").checked;

    const overlay = document.getElementById("progressOverlay");
    const progressBar = document.getElementById("progressBar");
    const progressText = document.getElementById("progressText");

    overlay.style.display = "flex";
    progressBar.value = 0;
    progressText.textContent = "Indexing in progress...";

    // Fake progress until request finishes
    let progress = 0;
    const interval = setInterval(() => {
        progress = Math.min(progress + Math.random() * 10, 95);
        progressBar.value = progress;
        progressText.textContent = `Indexing... ${Math.floor(progress)}%`;
    }, 500);

    fetch("/indexing", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            path: path,
            recursive: recursive,
        })
    })
    .then(res => res.json())
    .then(data => {
        clearInterval(interval);
        progressBar.value = 100;
        progressText.textContent = "Completed!";
        showPopup(`Indexed ${data.indexed_count} file(s).`);
    })
    .catch(() => {
        clearInterval(interval);
        progressBar.value = 0;
        progressText.textContent = "Failed!";
        showPopup("Indexing failed!")
    })
    .finally(() => {
        setTimeout(() => {
            overlay.style.display = "none";
        }, 800);
    });
});

document.getElementById("searchForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const query = document.getElementById("query").value;
    const fullText = document.getElementById("full_text").checked;

    callSearch(query, fullText);
});

document.addEventListener("keydown", function(e) {
    const overlay = document.getElementById("progressOverlay");
    if (overlay.style.display == "flex" && e.key === "Escape") {
        e.preventDefault();
    }
});

document.getElementById("progressOverlay").addEventListener("click", function(e) {
    e.stopPropagation();
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
                    <td><a href="#" class="open-file" data-path="${row.path}">${row.path}</a></td>
                    <td>${row.page_numbers.join(", ")}</td>
                    <td><ul>${row.match_terms.map(t => `<li>${t}</li>`).join('')}</ul></td>
                    <td><ul>${row.snippet.map(s => `<li>${s}</li>`).join('')}</ul></td>
                    <td class="tagging-cell" data-path="${row.path}">Loading...</td>
                </tr>
            `).join('')}
        </table>
    `;
    container.querySelectorAll('.open-file').forEach(a => {
        a.addEventListener('click', e => {
            e.preventDefault();
            openFile(a.dataset.path);
        });
    });

    fetch("/tagging/check", { method: "OPTIONS" })
        .then(res => {
            if (!res.ok) throw new Error("Tagging route not available");

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
        })
        .catch(err => {
            console.error("Tagging route missing:", err);
            document.querySelectorAll(".tagging-header, .tagging-cell").forEach(el => el.remove());
        });
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

async function openFile(path) {
  try {
    const res = await fetch('/open-file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Unknown error');
  } catch (err) {
    console.error('Error opening file', err.message);
  }
}
