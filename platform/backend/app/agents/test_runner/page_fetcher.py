"""
Page Fetcher — extract DOM summary from a target URL for script generation.

Navigates to the URL with Playwright and extracts a condensed representation
of the page structure (forms, buttons, links, inputs) for LLM context.
"""

import logging
from typing import Any, Dict

from playwright.async_api import Page

logger = logging.getLogger(__name__)

_DOM_EXTRACT_JS = """
(() => {
    const MAX_ITEMS = 200;
    const result = {
        title: document.title,
        url: location.href,
        forms: [],
        inputs: [],
        buttons: [],
        links: [],
        selects: [],
        textareas: [],
        headings: [],
    };

    document.querySelectorAll('input').forEach(el => {
        result.inputs.push({
            tag: 'input',
            type: el.type || 'text',
            name: el.name || '',
            id: el.id || '',
            placeholder: el.placeholder || '',
            value: el.value ? (el.type === 'password' ? '***' : el.value.substring(0, 50)) : '',
            selector: el.id ? `#${el.id}` : (el.name ? `[name="${el.name}"]` : ''),
            label: el.labels && el.labels[0] ? el.labels[0].textContent.trim().substring(0, 50) : '',
        });
    });

    document.querySelectorAll('button, [role="button"], input[type="submit"]').forEach(el => {
        result.buttons.push({
            tag: el.tagName.toLowerCase(),
            text: (el.textContent || el.value || '').trim().substring(0, 50),
            type: el.type || '',
            id: el.id || '',
            selector: el.id ? `#${el.id}` : '',
        });
    });

    document.querySelectorAll('a[href]').forEach((el, i) => {
        if (i >= MAX_ITEMS) return;
        result.links.push({
            text: el.textContent.trim().substring(0, 50),
            href: el.href.substring(0, 200),
            id: el.id || '',
        });
    });

    document.querySelectorAll('select').forEach(el => {
        const options = Array.from(el.options).slice(0, 10).map(o => o.textContent.trim().substring(0, 30));
        result.selects.push({
            name: el.name || '',
            id: el.id || '',
            options: options,
            selector: el.id ? `#${el.id}` : (el.name ? `[name="${el.name}"]` : ''),
        });
    });

    document.querySelectorAll('textarea').forEach(el => {
        result.textareas.push({
            name: el.name || '',
            id: el.id || '',
            placeholder: el.placeholder || '',
            selector: el.id ? `#${el.id}` : (el.name ? `[name="${el.name}"]` : ''),
        });
    });

    document.querySelectorAll('h1, h2, h3').forEach(el => {
        result.headings.push({
            tag: el.tagName.toLowerCase(),
            text: el.textContent.trim().substring(0, 80),
        });
    });

    return result;
})()
"""


async def fetch_page_context(page: Page, url: str) -> Dict[str, Any]:
    """Navigate to URL and extract DOM summary for LLM script generation."""
    logger.info("Page fetcher: navigating to %s", url)

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        logger.warning("Page fetcher: domcontentload failed: %s", e)
        try:
            await page.goto(url, wait_until="load", timeout=20000)
        except Exception as e2:
            logger.warning("Page fetcher: load failed: %s", e2)
            try:
                await page.goto(url, wait_until="commit", timeout=15000)
            except Exception:
                return {"title": "", "url": url, "error": f"Failed to navigate to {url}", "elements": {}}

    try:
        await page.wait_for_timeout(1000)
    except Exception:
        pass

    final_url = page.url
    title = await page.title()

    try:
        dom_summary = await page.evaluate(_DOM_EXTRACT_JS)
    except Exception as e:
        logger.warning("Page fetcher: DOM extraction failed: %s", e)
        dom_summary = {}

    element_lines = []
    for heading in dom_summary.get("headings", [])[:10]:
        element_lines.append(f"  [{heading['tag']}] {heading['text']}")
    for inp in dom_summary.get("inputs", [])[:30]:
        label_str = f" (label: {inp['label']})" if inp['label'] else ""
        element_lines.append(f"  <input type={inp['type']} name={inp['name']} id={inp['id']} placeholder={inp['placeholder']}{label_str}>")
    for btn in dom_summary.get("buttons", [])[:20]:
        element_lines.append(f"  <button id={btn['id']}>{btn['text']}</button>")
    for sel in dom_summary.get("selects", [])[:10]:
        opts = ", ".join(sel['options'][:5])
        element_lines.append(f"  <select name={sel['name']} id={sel['id']}> options: [{opts}]")
    for ta in dom_summary.get("textareas", [])[:10]:
        element_lines.append(f"  <textarea name={ta['name']} id={ta['id']} placeholder={ta['placeholder']}>")
    for link in dom_summary.get("links", [])[:15]:
        element_lines.append(f"  <a id={link['id']}>{link['text']} -> {link['href'][:80]}")

    return {
        "title": title,
        "url": final_url,
        "elements": dom_summary,
        "context_text": "\n".join(element_lines),
    }
