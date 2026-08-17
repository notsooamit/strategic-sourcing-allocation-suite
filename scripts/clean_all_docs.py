"""
Script to clean all markdown documentation across PR1 and SOP workspaces.
Converts all math formulas, LaTeX expressions, and currency symbols into clean,
standard, universal GitHub-flavored Markdown.
"""

import os
import glob
import re

def clean_markdown_content(text):
    # 1. Clean scrap percentage ranges
    text = text.replace(r'($2\%$ to $8\%$)', '(2% to 8%)')
    text = text.replace(r'($2\% - 8\%$)', '(2% to 8%)')
    text = text.replace(r'$2\%$ to $8\%$', '2% to 8%')
    text = text.replace(r'scrap ($2\%$ to $8\%$)', 'scrap (2% to 8%)')
    text = text.replace(r'scrap (2 to 8)', 'scrap (2% to 8%)')
    
    # 2. Clean inventory coverage ratios
    text = text.replace(r'($\frac{\text{OnHand}}{\text{SafetyStock}}$)', '`(On-Hand Stock / Safety Stock)`')
    text = text.replace(r'$$\text{InventoryCoverageRatio}_{m, p} = \frac{\text{OnHand}_{m, p}}{\text{SafetyStock}_{m, p}}$$ status', '`InventoryCoverageRatio[m, p] = OnHand[m, p] / SafetyStock[m, p]`')
    
    # 3. Clean anti-concentration volume bands
    text = text.replace(r'($15\%\text{ min} - 60\%\text{ max}$)', '(15% min to 60% max)')
    text = text.replace(r'($15\%$ to $60\%$)', '(15% to 60%)')
    text = text.replace(r'anti-concentration volume bands (15)', 'anti-concentration volume bands (15% min to 60% max)')
    
    # 4. Clean math symbols
    text = text.replace(r'($\lambda_{\text{risk}} = 0.15$)', '(λ_risk = 0.15)')
    text = text.replace(r'$\lambda_{\text{risk}} = 0.15$', 'λ_risk = 0.15')
    text = text.replace(r'($x \ge \text{MOQ} \cdot y$)', '`(x ≥ MOQ · y)`')
    text = text.replace(r'$x \ge \text{MOQ} \cdot y$', '`x ≥ MOQ · y`')
    text = text.replace(r'($\le 250\text{ PPM}$)', '(≤ 250 PPM)')
    text = text.replace(r'$\le 250\text{ PPM}$', '≤ 250 PPM')
    text = text.replace(r'($\ge 85$)', '(≥ 85)')
    text = text.replace(r'$\ge 85$', '≥ 85')
    text = text.replace(r'($P(\text{Delay} > 3\text{d})$)', '`P(Delay > 3d)`')
    text = text.replace(r'$P(\text{Delay} > 3\text{d})$', '`P(Delay > 3d)`')
    text = text.replace(r'($\mathcal{C}_{s, m}$)', '`(C[s, m])`')
    text = text.replace(r'($\mathcal{C}_{s,m}$)', '`(C[s, m])`')
    text = text.replace(r'$\mathcal{C}_{s, m}$', '`C[s, m]`')
    text = text.replace(r'$\mathcal{C}_{s,m}$', '`C[s, m]`')
    
    # 5. Clean currency ranges like $5.00 to $450.00
    text = text.replace('$5.00 to $450.00', '$5.00 to $450.00 USD')
    text = text.replace('$5.00 and $450.00', '$5.00 and $450.00 USD')
    text = text.replace('$29.50 to $149.00', '$29.50 to $149.00 USD')
    
    # 6. Clean POReleaseWeek formula
    raw_po_latex = r'$$\text{POReleaseWeek}(s, m, p, t) = t - \left\lceil \frac{\text{LeadTimeDays}_{s,m} + \text{TransitDays}_{s,p}}{7} \right\rceil$$'
    clean_po_box = "```\nPOReleaseWeek(s, m, p, t) = t - ceil((LeadTimeDays[s,m] + TransitDays[s,p]) / 7)\n```"
    text = text.replace(raw_po_latex, clean_po_box)
    
    raw_po_latex_2 = r'$$\text{POReleaseWeek}(s, m, p, t) = t - \left\lceil \frac{\text{LeadTimeDays}_{s, m} + \text{TransitDays}_{s, p}}{7} \right\rceil$$'
    text = text.replace(raw_po_latex_2, clean_po_box)

    raw_po_latex_3 = r'$$\text{POReleaseWeek} = t - \left\lceil \frac{\text{LeadTimeDays} + \text{TransitDays}}{7} \right\rceil$$'
    clean_po_box_3 = "```\nPOReleaseWeek = t - ceil((LeadTimeDays + TransitDays) / 7)\n```"
    text = text.replace(raw_po_latex_3, clean_po_box_3)

    return text

def process_all_docs():
    files = glob.glob('docs/*.md') + ['README.md'] + glob.glob('c:/Users/notso/Desktop/SOP/docs/*.md') + glob.glob('c:/Users/notso/Desktop/SOP/strategic_sourcing_spec/*.md')
    
    for fpath in files:
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                original = f.read()
            cleaned = clean_markdown_content(original)
            if cleaned != original:
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(cleaned)
                print(f"Updated: {fpath}")
            else:
                print(f"No change needed: {fpath}")

if __name__ == "__main__":
    process_all_docs()
