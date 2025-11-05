# NEW FEATURE:

Welcome to my I Ching Project! This repository is designed to offer an interactive experience with I Ching (The Book of Changes),
allowing users to perform traditional divination using methods such as the 50-yarrow stalk method, three-coin toss, or Meihua Yishu.
The repository also includes tools to calculate BaZi (八字) and the corresponding five elements (五行).

## Project Layout

```
├── src/iching
│   ├── cli/runner.py          # Console entry point
│   ├── core/                  # Domain logic (hexagrams, divination, BaZi, time utils)
│   ├── gui/app.py             # Gradio web interface
│   ├── integrations/          # AI + Najia adapters
│   └── services/session.py    # Session orchestration layer
├── data/                      # Textual resources (guaci, takashima, etc.)
├── legacy/                    # Archived pre-refactor scripts
├── tests/                     # Pytest-based smoke tests
└── iching5.py                 # CLI bootstrapper (uses the refactored package)
```

## Usage

```bash
# install dependencies
pip install -r requirements.txt

# run the interactive console
python iching5.py

# launch the Gradio UI
python gui.py

# execute automated tests
pytest
```

# Next steps

a. ENTIRELY RESTRUCTURE FOR CLARITY, use more class and subclass ✅ 10.23  
b. 纠正山地剥的错误binary code ✅ 10.24  
c. 校对傅佩荣 ✅ 10.27  
d. meihua make 3 3digit nums ✅ 10.24  
e. count and classify jixiong in each yao, rate ✅ 10.30  
f. generate flow chart ✅ 11.2  
g. 加入自然意象 ✅ 11.3  
h. 加入psutil, tqdm ✅ 11.4
i. integrate with AI for analysis and explanation ✅ 8.14 (2025)
j. add UI with Gradio ✅ 9.4
k. 八卦纳甲 卦分八宫 旺相休囚和生旺墓绝 十二长生 世应 六亲 六神 用神等 ✅ 11.3
l. complete titled database for all 64 hexagrams ✅ 11.4
m. total restructure ✅ 11.4
n. changed UI to streamlit ✅ 11.5

# DISCLAIMER AND WAIVER OF LIABILITY
# WARNING: THE MAKEFILE IN THIS REPOSITORY CONTAINS COMMANDS THAT MAY RESULT IN THE PERMANENT DELETION OF DATA OR SYSTEM DAMAGE.
## By accessing and using this repository, including running any commands within the Makefile, you acknowledge and agree to the following:

1. Assumption of Risk: You understand that the Makefile included in this repository may contain commands that could lead to the irreversible deletion of files, data loss, or system-level changes. Running these commands is entirely at your own risk.

2. No Liability: Under no circumstances shall the creator(s) or contributors of this repository be liable for any damages, loss of data, or harm resulting from the use of this Makefile, regardless of whether such damages were foreseeable. This includes, but is not limited to, damage to your computer systems, data corruption, or operational failure.

3. No Warranty: This repository and all files within it are provided "as is," without any warranty, express or implied, including but not limited to the implied warranties of merchantability, fitness for a particular purpose, or non-infringement. The creator(s) of this repository do not guarantee the Makefile will function as expected or without risk.

4. User Responsibility: By using this repository, you agree to assume all responsibility for any actions you take. You accept full liability for any consequences resulting from running the Makefile or other files, including but not limited to the loss or corruption of data, damage to hardware or software, and security vulnerabilities.

## Acknowledgment
### By proceeding, you confirm that you have read, understood, and agreed to this disclaimer. You also confirm that you are acting with full awareness of the potential consequences and assume all associated risks.

# DO NOT RUN THIS MAKEFILE UNLESS YOU ARE PREPARED FOR PERMANENT DATA LOSS OR SYSTEM DAMAGE. USE ONLY IN A SECURE, ISOLATED ENVIRONMENT FOR TESTING PURPOSES.
