# 🌐 US Trade Intelligence Dashboard

## 資料夾結構

```
CIS438/project/
├── main.py          ← 進入點，在這裡啟動 app
├── sidebar.py       ← 左側篩選器
├── view.py          ← 五個 Tab 的所有圖表
├── requirements.txt ← 需要安裝的套件
└── data/            ← 放資料的資料夾
    ├── country.xlsx
    ├── enduse_exports.xlsx
    └── enduse_imports.xlsx
```

## 安裝步驟（只需要做一次）

1. 打開 Terminal
2. 進入你的專案資料夾：
   ```bash
   cd ~/Desktop/CIS438/project
   ```
3. 安裝套件：
   ```bash
   pip install -r requirements.txt
   ```

## 啟動 App

```bash
cd ~/Desktop/CIS438/project
streamlit run main.py
```

瀏覽器會自動打開 http://localhost:8501

## 如果老師要你當場修改

| 老師要求 | 去哪裡改 | 改什麼 |
|---------|---------|--------|
| 換地圖顏色 | view.py Tab1 | `color_continuous_scale="Blues"` 換成其他顏色名稱 |
| 排行榜顯示更多 | sidebar.py | `options=[10, 15, 20]` 加數字 |
| 改圖表標題 | view.py 各 Tab | 找 `title=` 那一行 |
| 換預設比較國家 | sidebar.py | 找 `index=country_list.index("China")` |

## 常用顏色名稱（Plotly）

`Blues` `Reds` `Greens` `Viridis` `YlOrRd` `RdBu` `Plasma` `Turbo`
