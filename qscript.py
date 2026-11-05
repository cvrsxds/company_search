
import os
import re
from playwright.sync_api import sync_playwright

PATH_TO_VIDEO_FOLDER = "./video"

CURSOR_SCRIPT = r"""
(() => {
    function createCursor() {
        if (!document.body) return;

        if (document.getElementById("custom-cursor")) return;

        const cursor = document.createElement("div");
        cursor.id = "custom-cursor";

        cursor.style.cssText =
            "position:fixed !important;" +
            "top:0 !important;" +
            "left:0 !important;" +
            "width:32px !important;" +
            "height:32px !important;" +
            "pointer-events:none !important;" +
            "z-index:2147483647 !important;" +
            "transform:translate(-2px,-2px) !important;";

        cursor.innerHTML =
            '<svg width="32" height="32" viewBox="0 0 32 32">' +
            '<path d="M3 2 L3 25 L9 19 L14 29 L18 27 L13 17 L23 17 Z" ' +
            'fill="white" stroke="black" stroke-width="1.5" ' +
            'stroke-linejoin="round"/>' +
            '</svg>';

        const highlight = document.createElement("div");
        highlight.id = "cursor-highlight";

        highlight.style.cssText =
            "position:fixed !important;" +
            "top:0 !important;" +
            "left:0 !important;" +
            "width:45px !important;" +
            "height:45px !important;" +
            "border-radius:50% !important;" +
            "background:rgba(255,220,0,0.25) !important;" +
            "border:2px solid rgba(255,200,0,0.8) !important;" +
            "pointer-events:none !important;" +
            "z-index:2147483646 !important;" +
            "transform:translate(-50%,-50%) !important;";

        document.body.appendChild(highlight);
        document.body.appendChild(cursor);

        document.addEventListener("mousemove", function(event) {
            cursor.style.left = event.clientX + "px";
            cursor.style.top = event.clientY + "px";

            highlight.style.left = event.clientX + "px";
            highlight.style.top = event.clientY + "px";
        }, true);
    }

    const observer = new MutationObserver(createCursor);

    observer.observe(document, {
        childList: true,
        subtree: true
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", createCursor);
    } else {
        createCursor();
    }
})();
"""


def CaptureVideo(url, company_name, language, country, postcode, city, street, house_no):

    os.makedirs(PATH_TO_VIDEO_FOLDER, exist_ok=True)

    # Подготавливаем название видео
    safe_city = re.sub(r'[\\/:*?"<>|]', "_", city.strip())

    if not safe_city:
        safe_city = re.sub(r'[\\/:*?"<>|]', "_", company_name.strip())

    if not safe_city:
        safe_city = "video"

    browser = None
    context = None
    video = None
    video_temp_path = None

    try:
        with sync_playwright() as p:

            browser = p.chromium.launch(headless=False)

            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                record_video_dir=os.path.abspath(PATH_TO_VIDEO_FOLDER),
                record_video_size={"width": 1280, "height": 720}
            )

            # Добавляем курсор на все страницы
            context.add_init_script(CURSOR_SCRIPT)

            page = context.new_page()
            video = page.video

            # Функция плавного перемещения курсора
            def move_to_element(locator):

                locator.wait_for(
                    state="visible",
                    timeout=30000
                )

                box = locator.bounding_box()

                if box is None:
                    raise Exception("Element coordinates not found")

                x = box["x"] + box["width"] / 2
                y = box["y"] + box["height"] / 2

                page.mouse.move(x, y, steps=40)
                page.wait_for_timeout(500)

                return x, y

            # Поиск поисковой строки
            def get_search_box():

                search_box = page.locator(
                    'textarea[name="q"], input[name="q"]'
                ).first

                search_box.wait_for(
                    state="visible",
                    timeout=30000
                )

                return search_box

            # Ищем результаты поиска с повторными попытками
            def search_with_retries(search_query):

                for attempt in range(1, 4):

                    print(f"Search attempt: {attempt}/3")

                    if attempt == 1:
                        page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=60000
                        )
                    else:
                        page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=60000
                        )

                    page.wait_for_timeout(3000)

                    page.evaluate(CURSOR_SCRIPT)

                    search_box = get_search_box()

                    x, y = move_to_element(search_box)
                    page.mouse.click(x, y)

                    # Вводим запрос посимвольно
                    for char in search_query:
                        page.keyboard.insert_text(char)
                        page.wait_for_timeout(100)

                    print(f"Search query entered: {search_query}")

                    page.wait_for_timeout(1000)
                    page.keyboard.press("Enter")

                    print("Search submitted")

                    # Ожидаем появления результатов
                    results = page.locator(
                        'a[data-testid="result-title-a"]:visible, '
                        'a.result__a:visible'
                    ).first

                    try:
                        results.wait_for(
                            state="visible",
                            timeout=20000
                        )

                        print("Search results found")
                        return results

                    except Exception:

                        error_text = page.locator("body").inner_text(
                            timeout=10000
                        )

                        print("Search page did not return results")

                        if (
                            "server encountered an error" in error_text.lower()
                            or "oops" in error_text.lower()
                        ):
                            print("DuckDuckGo server error. Retrying...")
                            page.wait_for_timeout(5000)
                            continue

                        print("Page content:")
                        print(error_text[:500])

                raise Exception(
                    "Could not get search results after 3 attempts"
                )

            # Формируем поисковый запрос
            search_query = f"Magento developer in {city}"

            print("Opening search page...")

            # Запускаем поиск
            first_result = search_with_retries(search_query)

            page.wait_for_timeout(2000)

            # Перемещаем курсор к первой ссылке
            x, y = move_to_element(first_result)

            # Нажимаем на первую ссылку
            page.mouse.click(x, y)

            print("First result clicked")

            # Ждём перехода на сайт
            page.wait_for_timeout(7000)

            print(f"Website opened: {page.url}")

            # Оставляем сайт открытым для записи
            page.wait_for_timeout(10000)

            print("Finishing video recording...")

            # Завершаем запись видео
            context.close()
            context = None

            # Получаем путь после завершения записи
            video_temp_path = video.path()

            browser.close()
            browser = None

        # Проверяем временный файл
        if not video_temp_path or not os.path.exists(video_temp_path):
            raise Exception("Video file was not created")

        # Формируем конечный путь
        video_path = os.path.abspath(
            os.path.join(
                PATH_TO_VIDEO_FOLDER,
                safe_city + ".webm"
            )
        )

        # Переименовываем видео
        os.replace(video_temp_path, video_path)

        print("Video recording finished")
        print(f"Video saved: {video_path}")

        return video_path

    except Exception as e:

        print(f"Error for {company_name}: {e}")

        if context:
            try:
                context.close()
            except Exception:
                pass

        if browser:
            try:
                browser.close()
            except Exception:
                pass

        return None