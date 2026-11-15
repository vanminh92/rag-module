"""Real Edge + Streamlit + Ollama checks; never seed an answer or a citation."""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
from io import BytesIO

import httpx
from playwright.sync_api import sync_playwright, expect, TimeoutError as PlaywrightTimeout
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'ui_workbench'
SHOTS = OUT / 'screenshots'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8504)
    parser.add_argument('--browser', default='/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')
    args = parser.parse_args()
    SHOTS.mkdir(parents=True, exist_ok=True)
    checks = []
    complete = False
    def record(name, **extra):
        checks.append({'check': name, 'passed': True, **extra})
        print(name, extra, flush=True)
    log = (OUT / 'browser_server.log').open('w')
    server = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', 'streamlit_qa_app.py',
        '--server.address', '127.0.0.1', '--server.port', str(args.port), '--server.headless', 'true',
        '--server.fileWatcherType', 'none'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    url = f'http://127.0.0.1:{args.port}'
    try:
        for _ in range(150):
            try:
                if httpx.get(url+'/_stcore/health', timeout=1).status_code == 200:break
            except httpx.HTTPError:pass
            time.sleep(.2)
        else:raise RuntimeError('Streamlit did not start')
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser, headless=True)
            context = browser.new_context(viewport={'width':1440,'height':900}, permissions=['clipboard-read','clipboard-write'])
            page = context.new_page()
            console_errors = []
            page.on('pageerror', lambda e: console_errors.append(str(e)))
            page.goto(url)
            field = page.get_by_placeholder('Hỏi bất kỳ điều gì trong sổ tay…')
            field.wait_for();page.wait_for_timeout(1400)
            def screenshot(name):
                page.locator('main').evaluate('(e)=>e.scrollTop=0')
                page.screenshot(path=str(SHOTS/name))
            def choose(label, value):
                for attempt in range(3):
                    try:
                        combo = page.get_by_test_id('stSelectbox').filter(has_text=label).get_by_role('combobox')
                        combo.click(timeout=3000)
                        page.get_by_role('option',name=value,exact=True).click(timeout=3000)
                        page.wait_for_timeout(450)
                        return
                    except (PlaywrightTimeout, AssertionError):
                        page.keyboard.press('Escape');page.wait_for_timeout(700)
                        if attempt==2:raise
            def theme(name):
                for attempt in range(3):
                    try:
                        page.keyboard.press('Escape')
                        page.get_by_role('button',name='Main menu',exact=True).click()
                        expect(page.get_by_role('menu')).to_be_visible(timeout=3000)
                        print('Theme menu:',page.get_by_role('menu').all_text_contents(),flush=True)
                        page.get_by_role('menu').get_by_text(re.compile(name,re.I)).first.click(timeout=3000)
                        page.keyboard.press('Escape')
                        page.wait_for_timeout(500)
                        return
                    except (PlaywrightTimeout, AssertionError):
                        page.keyboard.press('Escape');page.wait_for_timeout(500)
                        if attempt==2:
                            print('Native menu diagnostic:',page.get_by_role('menu').all_text_contents(),flush=True)
                            page.screenshot(path=str(SHOTS/'theme_error.png'))
                            raise
            def overflow():
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            overflow();screenshot('desktop_empty.png')
            assert field.bounding_box()['y'] + field.bounding_box()['height'] <= 900, field.bounding_box()
            record('desktop_1440x900_empty_composer_visible')
            question = 'Sinh viên đại học chính quy tự đăng ký học phần từ học kỳ nào?'
            field.fill(question);field.press('Enter')
            try:
                page.get_by_text('Đang tìm nguồn, tổng hợp và kiểm tra bằng chứng…',exact=True).wait_for(timeout=15000)
                screenshot('loading.png')
            except Exception:pass
            source = page.get_by_role('button', name='[1] Sổ tay K50 · Trang 15', exact=False).first
            source.wait_for(timeout=240000)
            source.click()
            expect(page.get_by_role('spinbutton',name='Trang PDF')).to_have_value('15')
            frame = page.frame_locator('iframe[src*="streamlit_pdf_viewer"]').last
            frame.locator('#canvas_page_15').wait_for(timeout=30000)
            record('citation_opens_original_physical_page_15',question=question)
            page.get_by_text('Developer mode',exact=True).click()
            expect(page.get_by_text('Số lần gửi đến backend trong phiên: 1',exact=True)).to_be_visible()
            page.get_by_role('button',name='Sau',exact=False).first.click()
            expect(page.get_by_role('spinbutton',name='Trang PDF')).to_have_value('16')
            frame.locator('#canvas_page_16').wait_for()
            page.get_by_role('button',name='Trước',exact=False).first.click()
            expect(page.get_by_role('spinbutton',name='Trang PDF')).to_have_value('15')
            # Native widgets, actual viewer zoom and explicit fallback.
            zoom = page.get_by_test_id('stSelectbox').filter(has_text='Thu phóng').get_by_role('combobox')
            choose('Thu phóng','125%')
            frame.locator('#canvas_page_15').wait_for()
            engine = page.get_by_test_id('stSelectbox').filter(has_text='Trình xem').get_by_role('combobox')
            choose('Trình xem','Bản dự phòng')
            page.get_by_text('Bản xem chỉ gồm trang 15 của PDF gốc (220 trang).',exact=True).wait_for()
            with page.expect_download() as download:
                page.get_by_role('button',name='Tải trang này',exact=True).click()
            data = Path(download.value.path()).read_bytes()
            document = PdfReader(BytesIO(data))
            assert len(document.pages)==1 and 'Từ học kỳ thứ hai' in ' '.join(document.pages[0].extract_text().split())
            screenshot('desktop_fallback.png')
            record('fallback_and_download_contain_actual_page_15')
            choose('Trình xem','PDF.js')
            choose('Thu phóng','Vừa chiều rộng')
            page.get_by_role('button',name='Sao chép',exact=False).first.click()
            copied=page.evaluate('navigator.clipboard.readText()')
            assert 'học kỳ thứ hai' in copied
            record('copy_answer_uses_real_clipboard',characters=len(copied))
            expect(page.get_by_text('Số lần gửi đến backend trong phiên: 1',exact=True)).to_be_visible()
            record('pdf_page_zoom_fallback_copy_debug_did_not_repeat_backend')
            page.get_by_text('Developer mode',exact=True).click()
            expect(page.get_by_text('Số lần gửi đến backend trong phiên: 1',exact=True)).not_to_be_visible()
            screenshot('desktop_light.png')
            page.get_by_text('Đoạn được truy xuất · Trang PDF 15',exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(SHOTS/'desktop_evidence_excerpt.png'))
            page.locator('.st-key-pdf_panel').evaluate('(e)=>e.scrollTop=0')
            theme('Dark')
            screenshot('desktop_dark.png')
            color=page.get_by_test_id('stApp').evaluate('(e)=>getComputedStyle(e).backgroundColor')
            assert color=='rgb(11, 18, 32)',color
            record('native_dark_theme',background=color)
            theme('Light')
            page.get_by_role('button',name='Đóng PDF',exact=False).click()
            page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(1200)
            overflow();screenshot('mobile_chat.png')
            page.get_by_role('button',name='[1] Sổ tay K50 · Trang 15',exact=False).first.click()
            page.get_by_role('button',name='Quay lại hội thoại',exact=False).wait_for()
            expect(page.get_by_role('spinbutton',name='Trang PDF')).to_have_value('15')
            page.frame_locator('iframe[src*="streamlit_pdf_viewer"]').last.locator('#canvas_page_15').wait_for(timeout=30000)
            page.wait_for_timeout(350)
            screenshot('mobile_evidence.png')
            overflow();record('mobile_390px_separate_evidence_screen')
            page.get_by_role('button',name='Quay lại hội thoại',exact=False).click()
            page.set_viewport_size({'width':1024,'height':900});page.wait_for_timeout(1000)
            page.get_by_role('button',name='[1] Sổ tay K50 · Trang 15',exact=False).first.click()
            page.get_by_role('dialog').wait_for()
            page.frame_locator('iframe[src*="streamlit_pdf_viewer"]').last.locator('#canvas_page_15').wait_for(timeout=30000)
            page.wait_for_timeout(350)
            screenshot('tablet_evidence.png')
            record('tablet_1024px_pdf_dialog_rendered')
            page.get_by_role('button',name='Quay lại hội thoại',exact=False).click()
            page.set_viewport_size({'width':1440,'height':900});page.wait_for_timeout(1000)
            # A second real chat, without changing the original prompt/model.
            page.get_by_role('button',name='Trò chuyện mới',exact=False).click()
            field.fill('Ở trình độ đại học, học phần tiên quyết phải được tích lũy khi nào?');field.press('Enter')
            page.get_by_role('button',name='[1] Sổ tay K50 · Trang 9',exact=False).first.wait_for(timeout=240000)
            page.get_by_role('button',name=question[:40],exact=False).first.click()
            page.get_by_role('button',name='[1] Sổ tay K50 · Trang 15',exact=False).first.wait_for()
            page.get_by_text('Developer mode',exact=True).click()
            expect(page.get_by_text('Số lần gửi đến backend trong phiên: 2',exact=True)).to_be_visible()
            record('two_real_chats_and_history_switch_preserve_answers_without_inference')
            page.get_by_text('Developer mode',exact=True).click()
            expect(page.get_by_text('Số lần gửi đến backend trong phiên: 2',exact=True)).not_to_be_visible()
            screenshot('history.png')
            if console_errors:raise AssertionError(console_errors)
            record('no_browser_page_errors')
            context.close();browser.close()
            complete = True
    finally:
        (OUT/'browser_checks.json').write_text(json.dumps({'app':'streamlit_qa_app.py','backend':'actual local RAG + Ollama; no seeded replies','complete':complete,'checks_passed':len(checks),'checks':checks},ensure_ascii=False,indent=2)+'\n')
        server.terminate()
        try:server.wait(timeout=8)
        except subprocess.TimeoutExpired:server.kill();server.wait()
        log.close()


if __name__=='__main__':main()
