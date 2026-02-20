import re
import difflib

def apply_and_get_diff(old_text, new_text):
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
    if not diff:
        return ""
    return '\n'.join(diff[2:]) + '\n'

with open("src/talabat_wallet/styles.tcss", "r", encoding="utf-8") as f:
    original = f.read()

current = original
phases_output = []

# --- PHASE 1 ---
text = current

# #main-buttons block 1 remove
text = re.sub(r'/\* Fix grid spacing \*/\n#main-buttons \{[^\}]+\}\n\n', '', text)
# #main-buttons block 2 update
text = text.replace(
'''#main-buttons {
    layout: grid;
    grid-size: 2;
    grid-gutter: 1 2;
    height: auto;
    margin-bottom: 1;
}''',
'''/* Fix grid spacing */
#main-buttons {
    layout: grid;
    grid-size: 2;
    grid-gutter: 1 2;
    height: auto;
    margin-bottom: 1;
    padding: 0 1;
}''')

# CustomButton remove block 1
text = re.sub(r'CustomButton \{\n    width: 100%;\n    height: 1;\n    min-height: 1;\n    background: \$boost;\n    color: \$text;\n    border: none;\n    padding: 0;\n\}\n\n?', '', text)
# CustomButton block 2 update
text = text.replace(
'''CustomButton {
    background: $surface-lighten-1; /* 🏮 Brighter background for better contrast */
    color: $text;
}''',
'''CustomButton {
    width: 100%;
    height: 1;
    min-height: 1;
    background: $surface-lighten-1; /* 🏮 Brighter background for better contrast */
    color: $text;
    border: none;
    padding: 0;
}''')

# CustomButton:hover remove block 2
text = re.sub(r'CustomButton:hover \{\n    background: #0056ff !important;\n    color: white !important;\n\}\n\n', '', text)
# Update block 1
text = text.replace(
'''CustomButton:hover, Button:hover, .option-button:hover {
    background: $accent;
    color: white;
}''',
'''CustomButton:hover, Button:hover, .option-button:hover {
    background: #0056ff;
    color: white;
}''')

# CustomButton:focus remove block 2
text = re.sub(r'CustomButton:focus \{\n    background: #1c2228;\n    color: white;\n\}\n\n?', '', text)
# Update block 1
text = text.replace(
'''CustomButton:focus, Button:focus, Input:focus, Select:focus, .option-button:focus {
    outline: none;
    border: none;
    background: $boost;
    color: white;
    text-style: bold;
}''',
'''CustomButton:focus, Button:focus, Input:focus, Select:focus, .option-button:focus {
    outline: none;
    border: none;
    background: #1c2228;
    color: white;
    text-style: bold;
}''')

# #days-header duplicate
text = re.sub(r'#days-header \{\n    layout: grid;\n    grid-size: 7;\n    height: 3;\n    background: \$primary-darken-3;\n    color: \$accent;\n    border-bottom: heavy \$accent;\n    margin-top: 1;\n\}\n\n?', '', text)
text = text.replace(
'''#days-header {
    layout: grid;
    grid-size: 7;
    grid-columns: 1fr 1fr 1fr 1fr 1fr 1fr 1fr;
    height: 3;
    padding: 0 1;
    background: $primary-darken-2;
    border-bottom: heavy $primary;
}''',
'''#days-header {
    layout: grid;
    grid-size: 7;
    grid-columns: 1fr 1fr 1fr 1fr 1fr 1fr 1fr;
    height: 3;
    padding: 0 1;
    background: $primary-darken-3;
    color: $accent;
    border-bottom: heavy $accent;
    margin-top: 1;
}''')

# .day-cell duplicate
text = re.sub(r'\.day-cell \{\n    width: 100%;\n    height: 3;\n    content-align: center middle;\n    border: solid \$primary 10%;\n\}\n\n?', '', text)
text = text.replace(
'''.day-cell {
    width: 100%;
    height: 3;
    background: $surface;
    color: $text;
    border: solid $primary 10%;
    margin: 0;
    padding: 0;
}''',
'''.day-cell {
    width: 100%;
    height: 3;
    content-align: center middle;
    background: $surface;
    color: $text;
    border: solid $primary 10%;
    margin: 0;
    padding: 0;
}''')

phases_output.append(("PHASE 1", apply_and_get_diff(current, text)))
current = text

# --- PHASE 2 ---
# Remove unnecessary !important from window-mode and close button
text = current
text = text.replace(
'''    background: $boost !important;
    color: $text !important;
    text-style: none !important;''',
'''    background: $boost;
    color: $text;
    text-style: none;''')

text = text.replace(
'''    background: $primary-darken-2 !important;
    color: $text !important;
    text-style: none !important;''',
'''    background: $primary-darken-2;
    color: $text;
    text-style: none;''')

text = text.replace(
'''    background: #05070a !important; /* Keep fixed dark background */
    color: #ff8c00 !important;
    text-style: bold !important;''',
'''    background: #05070a; /* Keep fixed dark background */
    color: #ff8c00;
    text-style: bold;''')

text = text.replace(
'''.close-button:hover,
.close-icon-btn:hover {
    background: #d32f2f !important;
    color: black !important;
}''',
'''.close-button:hover,
.close-icon-btn:hover {
    background: #d32f2f;
    color: black;
}''')

text = text.replace(
'''.close-button:focus,
.close-icon-btn:focus {
    background: #8b0000 !important;
    color: white !important;
    outline: none;
}''',
'''.close-button:focus,
.close-icon-btn:focus {
    background: #8b0000;
    color: white;
    outline: none;
}''')

phases_output.append(("PHASE 2", apply_and_get_diff(current, text)))
current = text

# --- PHASE 3 ---
# Layout safety
text = current
text = text.replace(
'''#expense-list {
    height: 10;            /* 💌 Fixed height: Wallet NEEDS a list area for scrolling */
    overflow-y: auto;      /* ✅ ONLY window allowed a scrollbar */
    margin-top: 0;
    border: solid #1a2535;
    background: #0c1017;
}''',
'''#expense-list {
    height: auto;
    max-height: 10;        /* 💌 Safe max-height: Wallet NEEDS a list area for scrolling */
    overflow-y: auto;      /* ✅ ONLY window allowed a scrollbar */
    margin-top: 0;
    border: solid #1a2535;
    background: #0c1017;
}''')

text = text.replace(
'''/* Fix grid spacing */
#main-buttons {
    layout: grid;
    grid-size: 2;
    grid-gutter: 1 2;
    height: auto;
    margin-bottom: 1;
    padding: 0 1;
}''',
'''/* Fix grid spacing */
#main-buttons {
    layout: grid;
    grid-size: 2;
    grid-columns: 1fr 1fr;
    grid-gutter: 1 2;
    height: auto;
    margin-bottom: 1;
    padding: 0 1;
}''')

text = text.replace(
'''.modal-dialog {
    width: 85%;
    max-width: 120;
    height: auto;
    max-height: 85%;
    /* Removed background/border - Inherits from BaseWindow */
    padding: 1 2;
    overflow-y: auto;
}''',
'''.modal-dialog {
    box-sizing: border-box;
    width: 85%;
    max-width: 120;
    height: auto;
    max-height: 85%;
    /* Removed background/border - Inherits from BaseWindow */
    padding: 1 2;
    overflow-y: auto;
}''')

text = text.replace(
'''#add-order-dialog, #settlement-dialog, #db-mgmt-dialog, #order-details-dialog, #settlement-details-dialog, #wallet-dialog {
    width: 85%;
    max-width: 80;
    height: auto;
    max-height: 85%;
    /* Removed background/border */
    padding: 1;
    overflow: hidden;
    overflow-y: auto;
}''',
'''#add-order-dialog, #settlement-dialog, #db-mgmt-dialog, #order-details-dialog, #settlement-details-dialog, #wallet-dialog {
    box-sizing: border-box;
    width: 85%;
    max-width: 80;
    height: auto;
    max-height: 85%;
    /* Removed background/border */
    padding: 1;
    overflow: hidden;
    overflow-y: auto;
}''')

text = text.replace(
'''#txn-details-dialog {
    width: 90%;
    max-width: 60;
    height: auto;
    max-height: 85%;
    /* Removed background/border */
    padding: 1 2;
}''',
'''#txn-details-dialog {
    box-sizing: border-box;
    width: 90%;
    max-width: 60;
    height: auto;
    max-height: 85%;
    /* Removed background/border */
    padding: 1 2;
}''')

text = text.replace(
'''#shifts-history-dialog {
    height: auto;
    max-height: 80%;
    width: 85%;
    max-width: 90;
    layout: vertical;
    padding: 0 1;       /* 🚫 Was 1 2, reduced to minimize gap */
    overflow-y: hidden; /* 🚫 No scrollbar on this legacy backdrop */
}''',
'''#shifts-history-dialog {
    box-sizing: border-box;
    height: auto;
    max-height: 80%;
    width: 85%;
    max-width: 90;
    layout: vertical;
    padding: 0 1;       /* 🚫 Was 1 2, reduced to minimize gap */
    overflow-y: hidden; /* 🚫 No scrollbar on this legacy backdrop */
}''')

phases_output.append(("PHASE 3", apply_and_get_diff(current, text)))
current = text


# --- PHASE 4 ---
text = current

# Remove #global-footer
text = re.sub(r'\n\.window-mode #global-footer \{\n    tint: #000000 20%;\n\}', '', text)
text = re.sub(r'\n\.window-mode #global-footer \*:hover \{\n    background: #05070a; /\* Keep fixed dark background \*/\n    color: #ff8c00;\n    text-style: bold;\n\}', '', text)
text = text.replace(',\n.window-mode #global-footer', '')

# Remove .break-row
text = re.sub(r'\.break-row \{\n    height: auto;\n    min-height: 2;\n    align: center middle;\n    width: 100%;\n    margin-bottom: 1;\n\}\n\n?', '', text)
text = re.sub(r'\.break-options \{\n    padding: 1 0;\n    background: #1c2228; /\* Light Navy \*/\n\}\n\n?', '', text)

# Remove .expense-row
text = re.sub(r'\.expense-row \{\n    background: \$panel;\n    margin-bottom: 1;\n\}\n\n?', '', text)
text = re.sub(r'\.expense-row:hover \{\n    background: \$primary-darken-2;\n\}\n\n?', '', text)
text = re.sub(r'\.expense-row:hover Label \{\n    color: #4db8ff !important;\n    text-style: bold;\n\}\n\n?', '', text)
text = re.sub(r'\.expense-row:hover \{\n    background: \$primary-darken-1;\n\}\n\n?', '', text)

phases_output.append(("PHASE 4", apply_and_get_diff(current, text)))
current = text


# --- PHASE 5 ---
text = current

text = text.replace(
'''#txn-details-dialog.txn-details-in #title {
    background: $success-darken-1;
}

#txn-details-dialog.txn-details-out #title {
    background: $error-darken-1;
}''',
'''.txn-details-in #title {
    background: $success-darken-1;
}

.txn-details-out #title {
    background: $error-darken-1;
}''')

text = re.sub(r'\.has-shift \{\n    color: \$warning;\n    text-style: bold;\n\}\n\n?', '', text)
text = text.replace(
'''.day-cell.has-shift {
    border-bottom: heavy $success;
    background: $success 10%;
}''',
'''.day-cell.has-shift {
    border-bottom: heavy $success;
    background: $success 10%;
    color: $warning;
    text-style: bold;
}''')

text = re.sub(r'\.shifts-completed \{\n    color: \$success;\n    text-style: dim;\n\}\n\n?', '', text)
text = text.replace(
'''.day-cell.shifts-completed {
    border-bottom: heavy cyan;
    background: cyan 8%;
}''',
'''.day-cell.shifts-completed {
    border-bottom: heavy cyan;
    background: cyan 8%;
    color: $success;
    text-style: dim;
}''')

text = re.sub(r'\.today \{\n    background: \$accent 20%;\n    border: double \$accent;\n\}\n\n?', '', text)

phases_output.append(("PHASE 5", apply_and_get_diff(current, text)))
current = text


# --- PHASE 6 ---
text = current

text = text.replace(
'''#history-list {
    height: 1fr;
    width: 100%;
    background: $surface;
    border: none;
    overflow-y: scroll;
    scrollbar-size: 0 0; /* إخفاء السكرول بار تماماً لمنع الشريط الأسود */
}''',
'''#history-list {
    height: 1fr;
    width: 100%;
    background: $surface;
    border: none;
    overflow-y: hidden;
}''')

text = text.replace(
'''BaseWindow {
    width: auto;
    height: auto;
    max-width: 90%;          /* 📏 Requirement: Use max 90% */
    max-height: 90%;         /* 📏 Requirement: Use max 90% */
    background: #1c2228;
    border: heavy $primary; 
    padding: 0;
    margin: 0;
    display: block;
    position: absolute;''',
'''BaseWindow {
    width: auto;
    height: auto;
    max-width: 90%;          /* 📏 Requirement: Use max 90% */
    max-height: 90%;         /* 📏 Requirement: Use max 90% */
    background: #1c2228;
    border: heavy $primary; 
    padding: 0;
    margin: 0;
    position: absolute;''')

phases_output.append(("PHASE 6", apply_and_get_diff(current, text)))
current = text


# --- PHASE 7 ---
text = current

text = text.replace(
'''.window-mode #info-row *:hover {
    background: $primary-darken-2;
    color: $text;
    text-style: none;
}''',
'''.window-mode #info-row Static:hover,
.window-mode #info-row Label:hover {
    background: $primary-darken-2;
    color: $text;
    text-style: none;
}''')

text = text.replace(
'''.window-mode #wallets-row *:hover {
    background: $primary-darken-2;
    color: $text;
    text-style: none;
}''',
'''.window-mode #wallets-row WalletDisplay:hover {
    background: $primary-darken-2;
    color: $text;
    text-style: none;
}''')

phases_output.append(("PHASE 7", apply_and_get_diff(current, text)))
current = text

with open("src/talabat_wallet/styles.tcss", "w", encoding="utf-8") as f:
    f.write(current)

# Print strict format
output_lines = []
for phase_name, diff_content in phases_output:
    output_lines.append(phase_name)
    output_lines.append("")
    output_lines.append("```diff")
    output_lines.append(diff_content.strip("\n"))
    output_lines.append("```")
    output_lines.append("")

final_output = "\n".join(output_lines)
with open("refactor_output.txt", "w", encoding="utf-8") as f:
    f.write(final_output)

print("done")
