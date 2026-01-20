(function () {
    const form = document.getElementById("filters");
    if (!form) return;

    const qInput = form.querySelector('input[name="q"]');

    const categoryValue = document.getElementById("categoryValue");
    const regionValue = document.getElementById("regionValue");
    const districtValue = document.getElementById("districtValue");

    const categoryLabel = document.getElementById("categoryLabel");
    const regionLabel = document.getElementById("regionLabel");
    const districtLabel = document.getElementById("districtLabel");

    const districtBtn = document.getElementById("districtBtn");
    const districtList = document.getElementById("districtList");
    const districtSearch = document.getElementById("districtSearch");

    const dirList = document.getElementById("dirList");
    const dirChips = document.getElementById("dirChips");
    const dirClear = document.getElementById("dirClear");
    const dirApply = document.getElementById("dirApply");
    const dirSearch = document.getElementById("dirSearch");

    function escapeHtml(s) {
        return String(s).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
    }

    // ---- HTMX trigger ----
    function triggerFilter() {
        htmx.trigger(form, "filters-changed");
    }

    // ---- debounce ----
    function debounce(fn, wait) {
        let t = null;
        return function (...args) {
            clearTimeout(t);
            t = setTimeout(() => fn.apply(this, args), wait);
        };
    }

    // ---- dropdown close helpers ----
    const dropdownButtons = Array.from(document.querySelectorAll("[data-dropdown-toggle]"));

    function closeDropdownByMenuId(menuId) {
        const menu = document.getElementById(menuId);
        if (menu) menu.classList.add("hidden");
    }

    function closeAllDropdowns() {
        dropdownButtons.forEach(btn => closeDropdownByMenuId(btn.getAttribute("data-dropdown-toggle")));
    }

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeAllDropdowns();
    });

    // ---- districts loader ----
    async function loadDistricts(regionId) {
        districtList.innerHTML = "";
        if (!regionId) {
            districtBtn.disabled = true;
            districtList.innerHTML = `<li class="px-3 py-2 text-gray-500">Сначала выберите регион</li>`;
            return;
        }

        districtBtn.disabled = false;
        districtList.innerHTML = `<li class="px-3 py-2 text-gray-500">Загрузка...</li>`;

        const base = form.dataset.districtsUrl || "/panel/districts-json/";
        const url = base + "?region_id=" + encodeURIComponent(regionId);
        const res = await fetch(url, {headers: {"X-Requested-With": "XMLHttpRequest"}});
        const data = await res.json();

        const items = data.results || [];
        if (!items.length) {
            districtList.innerHTML = `<li class="px-3 py-2 text-gray-500">Нет районов</li>`;
            return;
        }

        districtList.innerHTML =
            `<li>
        <button type="button" class="w-full px-3 py-2 text-left hover:bg-gray-50"
                data-set="district" data-id="" data-label="Район">
          Все районы
        </button>
      </li>` +
            items.map(d => `
        <li class="district-item" data-name="${escapeHtml((d.name || "").toLowerCase())}">
          <button type="button" class="w-full px-3 py-2 text-left hover:bg-gray-50"
                  data-set="district" data-id="${d.id}" data-label="${escapeHtml(d.name)}">
            ${escapeHtml(d.name)}
          </button>
        </li>`).join("");
    }

    // district search
    if (districtSearch) {
        districtSearch.addEventListener("input", () => {
            const q = districtSearch.value.trim().toLowerCase();
            districtList.querySelectorAll(".district-item").forEach(li => {
                const name = li.dataset.name || "";
                li.style.display = name.includes(q) ? "" : "none";
            });
        });
    }

    // ---- directions chips ----
    function rebuildDirChips() {
        dirChips.innerHTML = "";
        const checked = dirList.querySelectorAll("input[type=checkbox]:checked");
        checked.forEach(ch => {
            const text = ch.closest("label").innerText.trim();
            const chip = document.createElement("button");
            chip.type = "button";
            chip.className =
                "inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-xs border border-gray-200 hover:bg-gray-200";
            chip.innerHTML = `${escapeHtml(text)} <span class="text-gray-500">✕</span>`;
            chip.addEventListener("click", () => {
                ch.checked = false;
                rebuildDirChips();
            });
            dirChips.appendChild(chip);
        });
    }

    if (dirSearch) {
        dirSearch.addEventListener("input", () => {
            const q = dirSearch.value.trim().toLowerCase();
            dirList.querySelectorAll(".dir-item").forEach(li => {
                const name = li.dataset.name || "";
                li.style.display = name.includes(q) ? "" : "none";
            });
        });
    }

    if (dirList) {
        dirList.addEventListener("change", (e) => {
            if (e.target && e.target.matches("input[type=checkbox]")) rebuildDirChips();
        });
    }

    if (dirClear) {
        dirClear.addEventListener("click", () => {
            dirList.querySelectorAll("input[type=checkbox]").forEach(ch => (ch.checked = false));
            rebuildDirChips();
            triggerFilter();
            closeDropdownByMenuId("dirMenu");
        });
    }

    if (dirApply) {
        dirApply.addEventListener("click", () => {
            triggerFilter();
            closeDropdownByMenuId("dirMenu");
        });
    }

    // ---- dropdown selection handler ----
    document.addEventListener("click", async (e) => {
        const btn = e.target.closest("button[data-set]");
        if (!btn) return;

        const set = btn.dataset.set;
        const id = btn.dataset.id || "";
        const label = btn.dataset.label || "";

        if (set === "category") {
            categoryValue.value = id;
            categoryLabel.textContent = label || "Категория";
            triggerFilter();
            closeDropdownByMenuId("categoryMenu");
            return;
        }

        if (set === "region") {
            regionValue.value = id;
            regionLabel.textContent = label || "Регион";

            districtValue.value = "";
            districtLabel.textContent = "Район";

            await loadDistricts(id);
            triggerFilter();
            closeDropdownByMenuId("regionMenu");
            return;
        }

        if (set === "district") {
            districtValue.value = id;
            districtLabel.textContent = label || "Район";
            triggerFilter();
            closeDropdownByMenuId("districtMenu");
        }
    });

    // ---- debounce search -> use form trigger (not per-input hx-get) ----
    if (qInput) {
        const debounced = debounce(() => triggerFilter(), 250);
        qInput.addEventListener("input", debounced);
        qInput.addEventListener("search", () => triggerFilter());
    }

    // ---- restore UI state from URL (back/forward/reload) ----
    function initFromUrl() {
        const params = new URLSearchParams(window.location.search);

        const q = params.get("q") || "";
        const cat = params.get("category") || "";
        const reg = params.get("region") || "";
        const dist = params.get("district") || "";
        const dirs = params.getAll("direction");

        if (qInput) qInput.value = q;

        categoryValue.value = cat;
        regionValue.value = reg;
        districtValue.value = dist;

        // label fallback: if you want exact names, you can embed map in template, but keeping simple
        if (cat) categoryLabel.textContent = categoryLabel.textContent; // keep selected label if already set
        if (reg) regionLabel.textContent = regionLabel.textContent;
        if (dist) districtLabel.textContent = districtLabel.textContent;

        if (reg) loadDistricts(reg);

        // directions checkboxes
        if (dirs.length) {
            dirList.querySelectorAll('input[type="checkbox"]').forEach(ch => {
                ch.checked = dirs.includes(ch.value);
            });
            rebuildDirChips();
        }
    }

    rebuildDirChips();
    initFromUrl();
})();
