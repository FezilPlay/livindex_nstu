document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('global-search');
    const resultsContainer = document.getElementById('search-results');

    searchInput.addEventListener('input', async (e) => {
        const query = e.target.value.trim();

        if (query.length < 2) {
            resultsContainer.classList.add('hidden');
            return;
        }

        try {
            const response = await fetch(`/search/?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (data.length > 0) {
                resultsContainer.innerHTML = data.map(item => {
                    // Логика формирования URL
                    let finalUrl = "";
                    let imageHtml = ""; // Переменная для хранения HTML картинки

                    if (item.type === 'city') {
                        // ДЛЯ ГОРОДА
                        finalUrl = `/${item.country_slug}/${item.slug}`;

                        // Если есть картинка города — выводим её, иначе плейсхолдер
                        if (item.image_url) {
                            imageHtml = `<img src="${item.image_url}" class="w-full h-full object-cover">`;
                        } else {
                            // Плейсхолдер для города без фото
                            imageHtml = `<div class="w-full h-full flex items-center justify-center text-[10px] text-gray-400 font-medium">Photo</div>`;
                        }
                    } else {
                        // ДЛЯ СТРАНЫ
                        finalUrl = `/${item.slug}`;

                        // Для страны выводим ТОЛЬКО флаг
                        if (item.flag_url) {
                            // Если флаг есть — выводим
                            imageHtml = `<img src="${item.flag_url}" class="w-full h-full object-contain px-2">`;
                        } else {
                            // Плейсхолдер для страны без флага (на всякий случай)
                            imageHtml = `<div class="w-full h-full flex items-center justify-center text-[10px] text-gray-400 font-medium">Flag</div>`;
                        }
                    }

                    // Рендерим конечную строку
                    return `
                        <a href="${finalUrl}" class="flex items-center gap-3 px-4 py-3 hover:bg-[#00D4AA]/10 transition-colors border-b border-gray-50 last:border-none">
                            <div class="w-12 h-10 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
                                ${imageHtml}
                            </div>
                            <div class="flex flex-col">
                                <span class="text-[14px] font-semibold text-[#0A2540]">${item.title}</span>
                                ${item.subtitle ? `<span class="text-[12px] text-[#546A7F]">${item.subtitle}</span>` : ''}
                            </div>
                        </a>
                    `;
                }).join('');
                resultsContainer.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Search error:', error);
        }
    });

    // Закрытие при клике вне поиска
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.relative')) {
            resultsContainer.classList.add('hidden');
        }
    });
});