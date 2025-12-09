#!/usr/bin/env python
"""Test script to verify js_on_load + async + dynamic import works in Gradio.

This tests the core mechanism needed to fix the NiiVue black screen bug.

Run:
    uv run python scripts/test_js_on_load.py

Then open http://localhost:7860 and check if the tests pass.
"""

import gradio as gr

# Test 1: Basic js_on_load execution
TEST1_HTML = '<div id="test1" style="padding:20px;background:#333;color:#fff;margin:10px;border-radius:8px;">Test 1: Waiting...</div>'
TEST1_JS = """
    element.innerText = 'Test 1: PASS - js_on_load executed!';
    element.style.background = '#228B22';
"""

# Test 2: Async IIFE pattern
TEST2_HTML = '<div id="test2" style="padding:20px;background:#333;color:#fff;margin:10px;border-radius:8px;">Test 2: Waiting...</div>'
TEST2_JS = """
    (async () => {
        element.innerText = 'Test 2: Async started...';
        await new Promise(r => setTimeout(r, 500));
        element.innerText = 'Test 2: PASS - Async/await works!';
        element.style.background = '#228B22';
    })();
"""

# Test 3: Dynamic import from CDN
TEST3_HTML = '<div id="test3" style="padding:20px;background:#333;color:#fff;margin:10px;border-radius:8px;">Test 3: Waiting...</div>'
TEST3_JS = """
    (async () => {
        element.innerText = 'Test 3: Loading NiiVue from CDN...';
        try {
            const mod = await import('https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js');
            if (mod.Niivue) {
                element.innerText = 'Test 3: PASS - NiiVue loaded! Niivue class available.';
                element.style.background = '#228B22';
            } else {
                element.innerText = 'Test 3: PARTIAL - Module loaded but no Niivue class';
                element.style.background = '#FFA500';
            }
        } catch(e) {
            element.innerText = 'Test 3: FAIL - ' + e.message;
            element.style.background = '#DC143C';
        }
    })();
"""

# Test 4: Canvas + WebGL2 check
TEST4_HTML = """
<div id="test4-container" style="padding:20px;background:#333;color:#fff;margin:10px;border-radius:8px;">
    <div id="test4-status">Test 4: Waiting...</div>
    <canvas id="test4-canvas" style="width:200px;height:100px;background:#000;margin-top:10px;"></canvas>
</div>
"""
TEST4_JS = """
    (async () => {
        const status = element.querySelector('#test4-status');
        const canvas = element.querySelector('#test4-canvas');

        status.innerText = 'Test 4: Checking WebGL2...';

        const gl = canvas.getContext('webgl2');
        if (!gl) {
            status.innerText = 'Test 4: FAIL - WebGL2 not supported';
            element.style.background = '#DC143C';
            return;
        }

        status.innerText = 'Test 4: Loading NiiVue...';
        try {
            const { Niivue } = await import('https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js');
            const nv = new Niivue({ logging: false, backColor: [0.2, 0.2, 0.3, 1] });
            await nv.attachToCanvas(canvas);
            nv.drawScene();

            status.innerText = 'Test 4: PASS - NiiVue attached to canvas!';
            status.style.color = '#90EE90';
        } catch(e) {
            status.innerText = 'Test 4: FAIL - ' + e.message;
            element.style.background = '#DC143C';
        }
    })();
"""

# Test 5: Full integration with props.value
TEST5_HTML = """
<div id="test5-container" style="padding:20px;background:#333;color:#fff;margin:10px;border-radius:8px;">
    <div id="test5-status">Test 5: Waiting...</div>
    <div id="test5-value" style="font-family:monospace;font-size:12px;margin-top:10px;"></div>
</div>
"""
TEST5_JS = """
    const status = element.querySelector('#test5-status');
    const valueDiv = element.querySelector('#test5-value');

    // Check if we can access props
    if (typeof props !== 'undefined') {
        status.innerText = 'Test 5: PASS - props object accessible!';
        status.style.color = '#90EE90';
        valueDiv.innerText = 'props.value = ' + JSON.stringify(props.value ?? null).substring(0, 100) + '...';
    } else {
        status.innerText = 'Test 5: FAIL - props not defined';
        element.style.background = '#DC143C';
    }
"""


with gr.Blocks(title="js_on_load Test Suite") as demo:
    gr.Markdown("""
    # NiiVue js_on_load Test Suite

    Testing if `js_on_load` supports the patterns we need for NiiVue:

    1. **Basic execution** - Does js_on_load run at all?
    2. **Async IIFE** - Does `(async () => { await ... })()` work?
    3. **Dynamic import** - Can we `await import()` from CDN?
    4. **Canvas + NiiVue** - Can we attach NiiVue to a canvas?
    5. **Props access** - Can we read `props.value`?

    All tests should show green "PASS" if our fix will work.
    """)

    with gr.Row():
        with gr.Column():
            gr.HTML(value=TEST1_HTML, js_on_load=TEST1_JS)
            gr.HTML(value=TEST2_HTML, js_on_load=TEST2_JS)
            gr.HTML(value=TEST3_HTML, js_on_load=TEST3_JS)

        with gr.Column():
            gr.HTML(value=TEST4_HTML, js_on_load=TEST4_JS)
            gr.HTML(value=TEST5_HTML, js_on_load=TEST5_JS)

    gr.Markdown("""
    ---
    **If all tests pass:** We can implement the `js_on_load` fix for NiiVue viewer.

    **If tests fail:** We'll need alternative approaches (gradio-iframe or enhanced 2D).
    """)


if __name__ == "__main__":
    print("Starting js_on_load test server...")
    print("Open http://localhost:7860 to see test results")
    demo.launch(server_port=7860)
