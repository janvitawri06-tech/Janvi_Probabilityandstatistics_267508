// CineMatch Bollywood Edition - Interactive UI

(function () {
    const searchInput = document.getElementById("movie-search");
    if (!searchInput) return; // Only run on home page

    const searchResults = document.getElementById("search-results");
    const selectedContainer = document.getElementById("selected-movies");
    const selectedCountBadge = document.getElementById("selected-count");
    const emptySelectionHint = document.getElementById("empty-selection-hint");
    const recommendBtn = document.getElementById("recommend-btn");
    const clearBtn = document.getElementById("clear-btn");
    const topNSelect = document.getElementById("top-n");

    const toggleCatalogBtn = document.getElementById("toggle-catalog-btn");
    const catalogPanel = document.getElementById("catalog-panel");
    const catalogGrid = document.getElementById("catalog-grid");

    const loadingEl = document.getElementById("loading");
    const errorBox = document.getElementById("error-box");
    const errorMsg = document.getElementById("error-msg");
    const resultsSection = document.getElementById("results-section");
    const spotlightContainer = document.getElementById("top-pick-spotlight");
    const comparisonChart = document.getElementById("comparison-chart");
    const comparisonTableBody = document.getElementById("comparison-table-body");
    const resultsGrid = document.getElementById("results-grid");
    const overlapSummary = document.getElementById("overlap-summary");
    const emptyRecsBox = document.getElementById("empty-recs-box");
    const examplesSection = document.getElementById("examples");

    const selected = new Map(); // movieId -> movie object
    let debounceTimer = null;

    function escapeHtml(text) {
        return String(text ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function getMonogram(title) {
        const words = String(title || "BM")
            .replace(/[^A-Za-z0-9 ]/g, " ")
            .trim()
            .split(/\s+/)
            .filter(Boolean);
        if (!words.length) return "BM";
        if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
        return (words[0][0] + words[1][0]).toUpperCase();
    }

    function renderPosterCard(movie, size = "md", isTop = false) {
        const title = escapeHtml(movie.display_title || movie.title);
        const year = movie.release_year ? String(movie.release_year) : "Year N/A";
        const monogram = escapeHtml(getMonogram(movie.display_title || movie.title));
        const topClass = isTop ? "poster-frame-top" : "";

        if (movie.poster_url) {
            return `<img src="${escapeHtml(movie.poster_url)}" alt="${title} poster" class="w-full h-full object-cover rounded-xl">`;
        }

        if (size === "sm") {
            return `
                <div class="poster-frame ${topClass} w-12 h-16 rounded-lg shrink-0 flex flex-col items-center justify-between p-1.5 text-center select-none">
                    <span class="text-[9px] uppercase tracking-wider text-amber-300/80 font-semibold">Hindi</span>
                    <span class="font-display font-bold text-sm text-white leading-none">${monogram}</span>
                    <span class="text-[9px] text-cine-soft">${escapeHtml(year)}</span>
                </div>
            `;
        }

        const dims = size === "lg" ? "w-32 sm:w-36 h-48 sm:h-52" : "w-24 h-36";
        return `
            <div class="poster-frame ${topClass} ${dims} rounded-xl shrink-0 flex flex-col justify-between p-3 text-center select-none shadow-lg">
                <div class="flex items-center justify-between text-[10px] text-amber-300/90 font-semibold uppercase tracking-wider">
                    <span>Bollywood</span>
                    <span>${escapeHtml(year)}</span>
                </div>
                <div class="my-auto px-1">
                    <div class="w-10 h-10 mx-auto mb-2 rounded-full bg-white/10 border border-white/15 flex items-center justify-center font-display font-bold text-base text-amber-300">
                        ${monogram}
                    </div>
                    <div class="text-xs font-semibold text-white leading-snug line-clamp-3">${title}</div>
                </div>
                <div class="text-[9px] text-gray-400 border-t border-white/10 pt-1">
                    Poster not in DB
                </div>
            </div>
        `;
    }

    function updateCatalogButtons() {
        if (!catalogGrid) return;
        catalogGrid.querySelectorAll("[data-catalog-id]").forEach((btn) => {
            const id = parseInt(btn.dataset.catalogId, 10);
            const isSelected = selected.has(id);
            btn.classList.toggle("border-cine-accent", isSelected);
            btn.classList.toggle("bg-cine-accent/15", isSelected);
            const badge = btn.querySelector(".catalog-select-state");
            if (badge) {
                badge.textContent = isSelected ? "Selected ✓" : "+ Add";
                badge.className = isSelected
                    ? "catalog-select-state text-xs font-semibold text-amber-300"
                    : "catalog-select-state text-xs font-medium text-cine-soft";
            }
        });
    }

    function updateControls() {
        const count = selected.size;
        recommendBtn.disabled = count === 0;
        clearBtn.disabled = count === 0;
        if (selectedCountBadge) {
            selectedCountBadge.textContent = String(count);
        }
        if (emptySelectionHint) {
            emptySelectionHint.classList.toggle("hidden", count > 0);
        }
        updateCatalogButtons();
    }

    function renderSelected() {
        selectedContainer.innerHTML = "";
        selected.forEach((movie, id) => {
            const genres = (movie.genre_list || []).slice(0, 2).join(" · ") || "Genre N/A";
            const yearText = movie.release_year ? `(${movie.release_year})` : "";
            const chip = document.createElement("div");
            chip.className =
                "selected-chip flex items-center gap-2.5 pl-2 pr-3 py-1.5 rounded-xl bg-cine-800 border border-cine-accent/45 text-sm shadow-sm";
            chip.innerHTML = `
                <div class="w-7 h-7 rounded-md bg-cine-accent/20 text-amber-300 font-display font-bold text-xs flex items-center justify-center shrink-0">
                    ${escapeHtml(getMonogram(movie.display_title || movie.title))}
                </div>
                <div class="min-w-0">
                    <div class="font-medium text-white leading-tight truncate max-w-[200px]">
                        ${escapeHtml(movie.display_title || movie.title)}
                        <span class="text-xs text-cine-soft font-normal">${escapeHtml(yearText)}</span>
                    </div>
                    <div class="text-[11px] text-cine-soft truncate">${escapeHtml(genres)}</div>
                </div>
                <button type="button" data-remove-id="${id}" aria-label="Remove ${escapeHtml(movie.display_title || movie.title)}"
                    class="ml-1 p-1 rounded-md text-cine-soft hover:text-white hover:bg-white/10 transition">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            `;
            selectedContainer.appendChild(chip);
        });

        selectedContainer.querySelectorAll("[data-remove-id]").forEach((btn) => {
            btn.addEventListener("click", () => {
                selected.delete(parseInt(btn.dataset.removeId, 10));
                renderSelected();
            });
        });

        updateControls();
    }

    function addMovie(movie) {
        if (!movie || !movie.movieId) return;
        if (!selected.has(movie.movieId)) {
            selected.set(movie.movieId, movie);
            renderSelected();
        }
        searchInput.value = "";
        searchResults.classList.add("hidden");
    }

    function toggleMovie(movie) {
        if (!movie || !movie.movieId) return;
        if (selected.has(movie.movieId)) {
            selected.delete(movie.movieId);
        } else {
            selected.set(movie.movieId, movie);
        }
        renderSelected();
    }

    // Live Bollywood search
    searchInput.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        const q = searchInput.value.trim();
        if (!q) {
            searchResults.classList.add("hidden");
            return;
        }
        debounceTimer = setTimeout(async () => {
            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&limit=15`);
                const data = await res.json();
                if (!data.results || !data.results.length) {
                    searchResults.innerHTML = `
                        <div class="p-4 text-sm text-cine-soft space-y-2">
                            <p class="text-white font-medium">No Bollywood movie matching "${escapeHtml(q)}" was found in our dataset.</p>
                            <p class="text-xs">Our database includes 22 Bollywood &amp; Indian titles such as <em>3 Idiots</em>, <em>Lagaan</em>, <em>PK</em>, <em>Taare Zameen Par</em>, <em>Golmaal</em>, and <em>Phir Hera Pheri</em>.</p>
                            <button type="button" id="open-catalog-from-empty" class="text-xs font-semibold text-amber-300 hover:text-amber-200 underline">
                                Browse all 22 available movies ↓
                            </button>
                        </div>
                    `;
                    const openBtn = document.getElementById("open-catalog-from-empty");
                    if (openBtn && catalogPanel) {
                        openBtn.addEventListener("click", () => {
                            catalogPanel.classList.remove("hidden");
                            searchResults.classList.add("hidden");
                            catalogPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
                        });
                    }
                } else {
                    searchResults.innerHTML = data.results
                        .map((m) => {
                            const isAdded = selected.has(m.movieId);
                            const genres = (m.genre_list || []).slice(0, 3).join(" · ") || "Genre N/A";
                            return `
                                <button type="button" data-search-id="${m.movieId}"
                                    class="w-full text-left px-4 py-3 hover:bg-white/5 transition flex items-center justify-between gap-3 border-b border-white/5 last:border-0">
                                    <div class="flex items-center gap-3 min-w-0">
                                        ${renderPosterCard(m, "sm")}
                                        <div class="min-w-0">
                                            <div class="font-medium text-sm text-white truncate">
                                                ${escapeHtml(m.display_title)}
                                                ${m.release_year ? `<span class="text-cine-soft font-normal">(${m.release_year})</span>` : ""}
                                            </div>
                                            <div class="text-xs text-cine-soft mt-0.5 truncate">
                                                ${escapeHtml(genres)} · <span class="text-amber-300/90">${escapeHtml(m.industry_tag)}</span>
                                            </div>
                                            <div class="text-[11px] text-gray-400 mt-0.5">${escapeHtml(m.rating_label)}</div>
                                        </div>
                                    </div>
                                    <span class="text-xs font-semibold px-2.5 py-1 rounded-lg shrink-0 ${
                                        isAdded
                                            ? "bg-amber-400/15 text-amber-300 border border-amber-400/30"
                                            : "bg-cine-accent/20 text-white border border-cine-accent/40"
                                    }">
                                        ${isAdded ? "Selected ✓" : "+ Select"}
                                    </span>
                                </button>
                            `;
                        })
                        .join("");

                    const byId = new Map(data.results.map((m) => [m.movieId, m]));
                    searchResults.querySelectorAll("[data-search-id]").forEach((btn) => {
                        btn.addEventListener("click", () => {
                            const movie = byId.get(parseInt(btn.dataset.searchId, 10));
                            addMovie(movie);
                        });
                    });
                }
                searchResults.classList.remove("hidden");
            } catch (err) {
                console.error(err);
            }
        }, 180);
    });

    // Hide dropdown on outside click
    document.addEventListener("click", (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.add("hidden");
        }
    });

    // Toggle full Bollywood catalog panel
    if (toggleCatalogBtn && catalogPanel) {
        toggleCatalogBtn.addEventListener("click", () => {
            const isHidden = catalogPanel.classList.toggle("hidden");
            toggleCatalogBtn.setAttribute("aria-expanded", String(!isHidden));
        });
    }

    // Wire catalog browse cards
    if (catalogGrid) {
        catalogGrid.querySelectorAll("[data-catalog-id]").forEach((btn) => {
            btn.addEventListener("click", () => {
                const movie = JSON.parse(btn.dataset.movieJson);
                toggleMovie(movie);
            });
        });
    }

    // Clear selection
    clearBtn.addEventListener("click", () => {
        selected.clear();
        renderSelected();
        resultsSection.classList.add("hidden");
        errorBox.classList.add("hidden");
        if (examplesSection) examplesSection.classList.remove("hidden");
    });

    function renderSpotlight(top) {
        const genres = (top.genre_list || []).map(
            (g) => `<span class="px-2.5 py-0.5 rounded-full text-xs bg-white/10 text-gray-200">${escapeHtml(g)}</span>`
        ).join("");
        const barClass = top.has_viewer_overlap ? "progress-fill-primary" : "progress-fill-secondary";

        spotlightContainer.innerHTML = `
            <div class="spotlight-card rounded-2xl p-6">
                <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-400/20 border border-amber-400/40 text-amber-300 text-xs font-bold uppercase tracking-wider">
                        <span>#1 Highest Recommended Match</span>
                    </div>
                    <span class="text-xs px-2.5 py-1 rounded-full bg-white/10 text-gray-200">${escapeHtml(top.match_method)}</span>
                </div>

                <div class="flex flex-col sm:flex-row gap-6 items-start">
                    ${renderPosterCard(top, "lg", true)}
                    <div class="flex-1 min-w-0 w-full">
                        <div class="flex flex-wrap items-baseline justify-between gap-4">
                            <div>
                                <h3 class="font-display text-2xl sm:text-3xl font-bold text-white">
                                    ${escapeHtml(top.display_title)}
                                    ${top.release_year ? `<span class="text-lg text-amber-300/90 font-normal">(${top.release_year})</span>` : ""}
                                </h3>
                                <p class="text-xs text-amber-300/90 font-medium mt-1">${escapeHtml(top.industry_tag)} · ${escapeHtml(top.rating_label)}</p>
                            </div>
                            <div class="text-left sm:text-right">
                                <div class="font-display text-3xl sm:text-4xl font-extrabold text-amber-300">${top.match_percentage}%</div>
                                <div class="text-xs text-cine-soft">Relative Match Score</div>
                            </div>
                        </div>

                        <div class="progress-track h-3 rounded-full mt-4">
                            <div class="${barClass} h-full rounded-full" style="width: ${top.match_percentage}%"></div>
                        </div>

                        <div class="flex flex-wrap gap-2 mt-4">${genres || '<span class="text-xs text-cine-soft">No genres listed</span>'}</div>

                        <div class="mt-4 p-3.5 rounded-xl bg-black/25 border border-white/10 text-sm text-gray-200">
                            <span class="font-semibold text-white">Why it is #1:</span>
                            ${escapeHtml(top.explanation)}
                        </div>

                        <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4 text-xs">
                            <div class="metric-pill rounded-xl p-2.5">
                                <div class="text-cine-soft">Viewer Overlap</div>
                                <div class="text-white font-semibold mt-0.5">
                                    ${top.has_viewer_overlap ? `${top.common_users} of ${top.source_total} viewers` : "None in dataset"}
                                </div>
                            </div>
                            <div class="metric-pill rounded-xl p-2.5">
                                <div class="text-cine-soft">Genre Match</div>
                                <div class="text-white font-semibold mt-0.5">${top.genre_score_pct}% overlap</div>
                            </div>
                            <div class="metric-pill rounded-xl p-2.5 col-span-2 sm:col-span-1">
                                <div class="text-cine-soft">Dataset Likes</div>
                                <div class="text-white font-semibold mt-0.5">${top.pos_count} positive (≥4.0★)</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderComparisonSection(recs) {
        const topPct = recs[0] ? recs[0].match_percentage : 100;

        comparisonChart.innerHTML = recs
            .map((r) => {
                const isTop = r.rank === 1;
                const barClass = r.has_viewer_overlap ? "progress-fill-primary" : "progress-fill-secondary";
                const diff = isTop ? "Top Pick" : `${(topPct - r.match_percentage).toFixed(1)}% below #1`;
                return `
                    <div class="space-y-1.5">
                        <div class="flex items-center justify-between gap-3 text-sm">
                            <div class="flex items-center gap-2 min-w-0">
                                <span class="w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold shrink-0 ${
                                    isTop ? "bg-amber-400 text-black" : "bg-cine-700 text-cine-soft"
                                }">${r.rank}</span>
                                <span class="font-medium text-white truncate">${escapeHtml(r.display_title)}</span>
                                ${r.release_year ? `<span class="text-xs text-cine-soft shrink-0">(${r.release_year})</span>` : ""}
                            </div>
                            <div class="flex items-center gap-2 shrink-0">
                                <span class="hidden sm:inline text-xs ${isTop ? "text-amber-300 font-semibold" : "text-cine-soft"}">${diff}</span>
                                <span class="font-display font-bold ${isTop ? "text-amber-300" : "text-white"}">${r.match_percentage}%</span>
                            </div>
                        </div>
                        <div class="progress-track h-2.5 rounded-full">
                            <div class="${barClass} h-full rounded-full" style="width: ${r.match_percentage}%"></div>
                        </div>
                    </div>
                `;
            })
            .join("");

        comparisonTableBody.innerHTML = recs
            .map((r) => {
                const isTop = r.rank === 1;
                return `
                    <tr class="${isTop ? "bg-amber-400/10" : "hover:bg-white/[0.03]"} border-b border-white/5 last:border-0">
                        <td class="py-3 px-3 font-bold ${isTop ? "text-amber-300" : "text-cine-soft"}">#${r.rank}</td>
                        <td class="py-3 px-3">
                            <div class="font-medium text-white">${escapeHtml(r.display_title)}</div>
                            <div class="text-xs text-cine-soft">${escapeHtml(r.industry_tag)}</div>
                        </td>
                        <td class="py-3 px-3 text-cine-soft">${r.release_year || "—"}</td>
                        <td class="py-3 px-3 text-xs text-cine-soft">${escapeHtml((r.genre_list || []).slice(0, 2).join(", ") || "N/A")}</td>
                        <td class="py-3 px-3 text-xs">
                            ${r.has_viewer_overlap
                                ? `<span class="text-emerald-300 font-medium">${r.common_users}/${r.source_total} viewers</span>`
                                : `<span class="text-cine-soft">Genre only</span>`}
                        </td>
                        <td class="py-3 px-3 text-xs text-white">${r.genre_score_pct}%</td>
                        <td class="py-3 px-3 text-right font-display font-bold ${isTop ? "text-amber-300" : "text-white"}">${r.match_percentage}%</td>
                    </tr>
                `;
            })
            .join("");
    }

    function renderRecommendationCards(recs) {
        resultsGrid.innerHTML = recs
            .map((r, i) => {
                const isTop = r.rank === 1;
                const delay = i * 45;
                const barClass = r.has_viewer_overlap ? "progress-fill-primary" : "progress-fill-secondary";
                const genres = (r.genre_list || []).slice(0, 3).map(
                    (g) => `<span class="px-2 py-0.5 rounded-md text-[11px] bg-white/5 border border-white/10 text-gray-300">${escapeHtml(g)}</span>`
                ).join("");

                return `
                    <article class="rec-card glass rounded-2xl p-5 card-hover flex flex-col justify-between ${
                        isTop ? "border-amber-400/50 ring-1 ring-amber-400/20" : ""
                    }" style="animation-delay: ${delay}ms">
                        <div>
                            <div class="flex items-start justify-between gap-3 mb-4">
                                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold ${
                                    isTop ? "bg-amber-400 text-black" : "bg-cine-700 text-gray-200"
                                }">
                                    #${r.rank} ${isTop ? "Top Match" : "Match"}
                                </span>
                                <span class="text-xs font-display font-bold ${isTop ? "text-amber-300" : "text-white"}">
                                    ${r.match_percentage}% Score
                                </span>
                            </div>

                            <div class="flex gap-4 items-start">
                                ${renderPosterCard(r, "md", isTop)}
                                <div class="min-w-0 flex-1">
                                    <h3 class="font-display font-bold text-lg text-white leading-snug">
                                        ${escapeHtml(r.display_title)}
                                    </h3>
                                    <div class="text-xs text-cine-soft mt-1">
                                        ${r.release_year ? `Released ${r.release_year}` : "Release year N/A"} · ${escapeHtml(r.industry_tag)}
                                    </div>
                                    <div class="text-xs text-amber-300/90 mt-1">
                                        ${escapeHtml(r.rating_label)}
                                    </div>
                                    <div class="flex flex-wrap gap-1.5 mt-2.5">
                                        ${genres || '<span class="text-xs text-cine-soft">No genres listed</span>'}
                                    </div>
                                </div>
                            </div>

                            <div class="mt-4">
                                <div class="flex justify-between text-xs mb-1.5">
                                    <span class="text-cine-soft">${escapeHtml(r.match_method)}</span>
                                    <span class="font-semibold text-white">${r.match_percentage}%</span>
                                </div>
                                <div class="progress-track h-2 rounded-full">
                                    <div class="${barClass} h-full rounded-full" style="width: ${r.match_percentage}%"></div>
                                </div>
                            </div>
                        </div>

                        <div class="mt-4 pt-3 border-t border-white/10 text-xs text-gray-300 leading-relaxed">
                            <span class="font-semibold text-white">Why recommended:</span>
                            ${escapeHtml(r.explanation)}
                        </div>
                    </article>
                `;
            })
            .join("");
    }

    async function fetchRecommendations() {
        if (selected.size === 0) return;

        const ids = Array.from(selected.keys()).join(",");
        const topN = topNSelect.value;

        errorBox.classList.add("hidden");
        emptyRecsBox.classList.add("hidden");
        resultsSection.classList.add("hidden");
        loadingEl.classList.remove("hidden");
        if (examplesSection) examplesSection.classList.add("hidden");

        try {
            const res = await fetch(`/api/recommend?movies=${encodeURIComponent(ids)}&top_n=${encodeURIComponent(topN)}`);
            const data = await res.json();
            loadingEl.classList.add("hidden");

            if (!res.ok) {
                errorMsg.textContent = data.error || "Could not load recommendations.";
                errorBox.classList.remove("hidden");
                return;
            }

            resultsSection.classList.remove("hidden");
            const recs = data.recommendations || [];

            if (!recs.length) {
                spotlightContainer.innerHTML = "";
                comparisonChart.innerHTML = "";
                comparisonTableBody.innerHTML = "";
                resultsGrid.innerHTML = "";
                emptyRecsBox.classList.remove("hidden");
                return;
            }

            if (data.has_viewer_overlap) {
                overlapSummary.textContent =
                    "Top picks combine real viewer overlap in our dataset with genre matching.";
                overlapSummary.className =
                    "px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30";
            } else {
                overlapSummary.textContent =
                    "Ranked by genre similarity & popularity (no shared viewer ratings in dataset for these picks).";
                overlapSummary.className =
                    "px-3 py-1 rounded-full text-xs font-medium bg-sky-500/15 text-sky-300 border border-sky-500/30";
            }

            renderSpotlight(recs[0]);
            renderComparisonSection(recs);
            renderRecommendationCards(recs);
        } catch (err) {
            loadingEl.classList.add("hidden");
            errorMsg.textContent = "Something went wrong while fetching recommendations. Please try again.";
            errorBox.classList.remove("hidden");
            console.error(err);
        }
    }

    recommendBtn.addEventListener("click", fetchRecommendations);

    // Quick-start Bollywood combo buttons
    document.querySelectorAll(".example-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const movies = JSON.parse(btn.dataset.moviesJson || "[]");
            selected.clear();
            movies.forEach((m) => selected.set(m.movieId, m));
            renderSelected();
            fetchRecommendations();
        });
    });

    renderSelected();
})();
