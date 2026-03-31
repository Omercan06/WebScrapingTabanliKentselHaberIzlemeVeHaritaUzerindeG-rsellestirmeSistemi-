let map;
let markers = [];
let newsData = [];

// Premium Color Suite
const categoryStyles = {
    "Trafik Kazası": { 
        color: "#f87171", // Red-400
        accent: "rgba(248, 113, 113, 0.2)",
        icon: "fas fa-car-side" 
    },
    "Yangın": { 
        color: "#fb923c", // Orange-400
        accent: "rgba(251, 146, 60, 0.2)",
        icon: "fas fa-fire" 
    },
    "Elektrik Kesintisi": { 
        color: "#facc15", // Yellow-400
        accent: "rgba(250, 204, 21, 0.2)",
        icon: "fas fa-bolt" 
    },
    "Hırsızlık": { 
        color: "#c084fc", // Purple-400
        accent: "rgba(192, 132, 252, 0.2)",
        icon: "fas fa-user-ninja" 
    },
    "Kültürel Etkinlikler": { 
        color: "#4ade80", // Green-400
        accent: "rgba(74, 222, 128, 0.2)",
        icon: "fas fa-masks-theater" 
    },
    "Diğer": { 
        color: "#94a3b8", // Slate-400
        accent: "rgba(148, 163, 184, 0.2)",
        icon: "fas fa-newspaper" 
    }
};

// Custom Premium Dark Map Style
const mapStyle = [
    { "elementType": "geometry", "stylers": [{ "color": "#111827" }] },
    { "elementType": "labels.text.fill", "stylers": [{ "color": "#94a3b8" }] },
    { "elementType": "labels.text.stroke", "stylers": [{ "color": "#111827" }] },
    { "featureType": "administrative", "elementType": "geometry", "stylers": [{ "color": "#4b5563" }] },
    { "featureType": "administrative.country", "elementType": "labels.text.fill", "stylers": [{ "color": "#94a3b8" }] },
    { "featureType": "road", "elementType": "geometry", "stylers": [{ "color": "#1f2937" }] },
    { "featureType": "road", "elementType": "labels.text.fill", "stylers": [{ "color": "#6b7280" }] },
    { "featureType": "water", "elementType": "geometry", "stylers": [{ "color": "#07090e" }] },
    { "featureType": "water", "elementType": "labels.text.fill", "stylers": [{ "color": "#334155" }] }
];

async function initMap() {
    const kocaeli = { lat: 40.7656, lng: 29.9403 };

    try {
        const { Map } = await google.maps.importLibrary("maps");
        const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

        map = new Map(document.getElementById("map"), {
            zoom: 11,
            center: kocaeli,
            mapId: "KOCAELI_NEWS_MAP_ID",
            styles: mapStyle,
            disableDefaultUI: true,
            zoomControl: true,
            backgroundColor: "#07090e"
        });

        // Set style via Options for better fallback
        map.setOptions({ styles: mapStyle });

        // Setup inputs and listeners FIRST so filters have default values
        setupEventListeners();
        fetchNews();
    } catch (error) {
        console.error("Map initialization failed:", error);
    }
}

function setupEventListeners() {
    document.getElementById('apply-filters').addEventListener('click', () => {
        showLoader();
        setTimeout(applyFilters, 300); // Slight delay for smoother feel
    });
    
    // İster: Filtrelerin sayfa yenilenmeden anında/dinamik çalışması
    const filterInputs = document.querySelectorAll('.checkbox-grid input, #district-select, .filter-group input[type="date"]');
    filterInputs.forEach(input => {
        input.addEventListener('change', () => {
             // Instantly apply filters when user changes date, category or district without losing map context
             applyFilters();
        });
    });
    
    document.getElementById('trigger-scrape').addEventListener('click', triggerScraping);
    
    // ZORUNLU İSTER: 3 günlük sınır varsayılanına dönüldü ()
    const today = new Date();
    const threeDaysAgo = new Date();
    threeDaysAgo.setDate(today.getDate() - 3);
    
    // Yyyy-mm-dd formülüne emniyetli çevirme
    const formatYMD = (date) => {
        const offset = date.getTimezoneOffset()
        date = new Date(date.getTime() - (offset*60*1000))
        return date.toISOString().split('T')[0]
    }
    
    document.getElementById('date-end').value = formatYMD(today);
    document.getElementById('date-start').value = formatYMD(threeDaysAgo);
}

function showLoader() {
    const container = document.getElementById('recent-news-list');
    container.innerHTML = '<div class="news-list-loader"><i class="fas fa-circle-notch fa-spin"></i> Veriler işleniyor...</div>';
}

async function fetchNews() {
    showLoader();
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/api/news`);
        if (response.ok) {
            const data = await response.json();
            newsData = data.data || [];
            console.log(`[API KÖPRÜSÜ] Backend'den ${newsData.length} adet veri çekildi. Örnek:`, newsData[0]);
        } else {
            console.warn("Backend API not reachable. Using mock data.");
            useMockData();
        }
    } catch (error) {
        console.warn("Error fetching news:", error);
        useMockData();
    }
    applyFilters();
}

function useMockData() {
    newsData = [
        {
            id: 'm1',
            title: "İzmit D-100'de Korkutan Kaza",
            type: "Trafik Kazası",
            locationText: "İzmit, Kocaeli",
            lat: 40.7666, lng: 29.9322,
            date: new Date().toISOString(),
            sourceName: "Özgür Kocaeli",
            url: "#"
        },
        {
            id: 'm2',
            title: "Gebze Sanayide Yangın Müdahalesi",
            type: "Yangın",
            locationText: "Gebze, Kocaeli",
            lat: 40.7890, lng: 29.4230,
            date: new Date().toISOString(),
            sourceName: "Demokrat Gebze",
            url: "#"
        },
        {
            id: 'm3',
            title: "Büyükşehir'den Kültür Sanat Buluşması",
            type: "Kültürel Etkinlikler",
            locationText: "Başiskele, Kocaeli",
            lat: 40.7050, lng: 29.9200,
            date: new Date().toISOString(),
            sourceName: "Kocaeli TV",
            url: "#"
        }
    ];
}

function applyFilters() {
    const startVal = document.getElementById('date-start').value;
    const endVal = document.getElementById('date-end').value;
    
    // Safely parse dates, defaulting to a huge range if empty
    const startDate = startVal ? new Date(startVal) : new Date(0);
    const endDate = endVal ? new Date(endVal) : new Date();
    endDate.setHours(23, 59, 59, 999);
    
    // Categories
    const categories = [];
    if (document.getElementById('cat-trafik').checked) categories.push("Trafik Kazası");
    if (document.getElementById('cat-yangin').checked) categories.push("Yangın");
    if (document.getElementById('cat-elektrik').checked) categories.push("Elektrik Kesintisi");
    if (document.getElementById('cat-hirsizlik').checked) categories.push("Hırsızlık");
    if (document.getElementById('cat-kultur').checked) categories.push("Kültürel Etkinlikler");
    
    const selectedDistrict = document.getElementById('district-select').value;
    
    const filteredData = newsData.filter(news => {
        const d = new Date(news.date);
        const inDate = d >= startDate && d <= endDate;
        const inCat = categories.includes(news.type);
        const inDistrict = selectedDistrict === "Tümü" || (news.locationText && news.locationText.includes(selectedDistrict));
        
        return inDate && inCat && inDistrict;
    });
    
    renderMarkers(filteredData);
    renderSidebarList(filteredData);
}

function clearMarkers() {
    markers.forEach(m => m.map = null);
    markers = [];
}

async function renderMarkers(data) {
    clearMarkers();
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
    const { InfoWindow } = await google.maps.importLibrary("maps");
    const infoWindow = new InfoWindow();

    // Track marker positions to detect and jitter overlaps
    const positionCounters = {};

    data.forEach(news => {
        if (!news.lat || !news.lng) return;
        
        let finalLat = news.lat;
        let finalLng = news.lng;

        // Jittering Logic: If multiple markers share exact coordinates, offset them slightly
        const coordKey = `${news.lat.toFixed(4)}_${news.lng.toFixed(4)}`;
        if (positionCounters[coordKey]) {
            // Add a small spiral/random offset (approx 10-20 meters)
            const count = positionCounters[coordKey];
            const angle = count * (Math.PI * 2 / 8); 
            const radius = 0.0003 * (1 + Math.floor(count / 8)); // Increase radius every 8 items
            finalLat += Math.cos(angle) * radius;
            finalLng += Math.sin(angle) * radius;
            positionCounters[coordKey]++;
        } else {
            positionCounters[coordKey] = 1;
        }

        const style = categoryStyles[news.type] || categoryStyles["Diğer"];
        
        const pin = new PinElement({
            background: style.color,
            borderColor: "#fff",
            glyphColor: "#fff",
            scale: 0.9
        });

        const marker = new AdvancedMarkerElement({
            map: map,
            position: { lat: finalLat, lng: finalLng },
            title: news.title,
            content: pin.element
        });

        marker.addListener("click", () => {
            let sources = [];
            if (news.sources) sources = news.sources;
            else if (news.url) sources = [{name: news.sourceName || 'Haber Kaynağı', url: news.url}];

            const content = `
                <div class="custom-info-window">
                    <div class="info-header">
                         <span class="news-badge" style="background: ${style.accent}; color: ${style.color}">
                            <i class="${style.icon}"></i> ${news.type}
                         </span>
                         <h3 class="info-title">${news.title}</h3>
                         <div class="news-footer">
                             <span><i class="fas fa-calendar-alt"></i> ${new Date(news.date).toLocaleDateString('tr-TR')}</span>
                             <span><i class="fas fa-map-marker-alt"></i> ${news.locationText || 'Kocaeli'}</span>
                         </div>
                    </div>
                    <div class="info-sources" style="margin-top: 10px;">
                        ${sources.map(s => `
                            <!-- Habere Git Butonu (Yeni Sekmede açılma garantili) -->
                            <a href="${s.url}" target="_blank" class="source-link" style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.05); padding:8px 12px; border-radius:6px; margin-top:8px; text-decoration:none; color:#f8fafc; border: 1px solid rgba(255,255,255,0.1); transition: all 0.2s;">
                                <span style="font-weight: 500;"><i class="fas fa-newspaper" style="color:${style.color}; margin-right:5px;"></i> ${s.name}</span>
                                <span style="background:${style.color}; color:#111827; padding:4px 10px; border-radius:4px; font-size:12px; font-weight:700; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">Habere Git <i class="fas fa-external-link-alt" style="margin-left:3px;"></i></span>
                            </a>
                        `).join('')}
                    </div>
                </div>
            `;
            infoWindow.setContent(content);
            infoWindow.open(map, marker);
        });
        markers.push(marker);
    });
}

function renderSidebarList(data) {
    const list = document.getElementById('recent-news-list');
    list.innerHTML = '';
    
    if (data.length === 0) {
        list.innerHTML = '<div class="news-list-empty">Seçili kriterlere göre haber bulunamadı.</div>';
        return;
    }

    const sorted = [...data].sort((a, b) => new Date(b.date) - new Date(a.date));
    
    sorted.forEach((news, index) => {
        const style = categoryStyles[news.type] || categoryStyles["Diğer"];
        const card = document.createElement('div');
        card.className = 'news-card';
        card.style.setProperty('--card-accent', style.color);
        card.style.animationDelay = `${index * 0.05}s`;
        
        card.innerHTML = `
            <div class="news-badge" style="background: ${style.accent}; color: ${style.color}">
                <i class="${style.icon}"></i> ${news.type}
            </div>
            <h4 class="news-title">${news.title}</h4>
            <div class="news-footer">
                <div class="news-meta-item">
                    <i class="fas fa-clock"></i>
                    ${new Date(news.date).toLocaleDateString('tr-TR')}
                </div>
                <div class="news-meta-item">
                    <i class="fas fa-location-dot"></i>
                    ${(news.locationText || 'Kocaeli').split(',')[0]}
                </div>
                <a href="${news.url}" target="_blank" class="sidebar-source-link" onclick="event.stopPropagation()">
                    <i class="fas fa-external-link-alt"></i>
                </a>
            </div>
        `;
        
        card.addEventListener('click', () => {
            if (news.lat && news.lng) {
                map.panTo({lat: news.lat, lng: news.lng});
                map.setZoom(13); // Changed from 14 to 13 for better overview
            }
        });
        
        list.appendChild(card);
    });
}

async function triggerScraping() {
    const btn = document.getElementById('trigger-scrape');
    const originalContent = btn.innerHTML;
    
    try {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Tarama Yapılıyor...';
        btn.disabled = true;
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/api/scrape`, { method: 'POST' });
        if (response.ok) {
            fetchNews();
        } else {
            alert("Hata: Tarama işlemi başarısız oldu.");
        }
    } catch (error) {
        console.error("Scraping error:", error);
        alert("Sunucuya bağlanılamadı.");
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

function loadGoogleMapsScript() {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${CONFIG.GOOGLE_MAPS_API_KEY}&loading=async&callback=initMap`;
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
}

window.initMap = initMap;
document.addEventListener('DOMContentLoaded', loadGoogleMapsScript);
