# 太空／真空場景 組合範例
> 適用範圍：orbit／vacuum 敘事場景（衛星、太空船、軌道站、星際物體等主體嵌在真空背景裡的構圖），
> 不含帶大氣層的行星表面場景（那類走一般 `outdoor_golden`/`night` PRESETS）
> 涵蓋工具：`space_lib.py`（全部函式）、`build_template.py`（`PRESETS["space"]`／
> `auto_space_fill()`／`set_ground_void()`／`audit_horizon_surfaces()`／`audit_horizon_line()`／
> `assert_disc_in_frame()`／`request_world_hook()`）
> 最後更新：2026-09-13（從 SKILL.md §10.5 抽出獨立成檔，內容未刪減——原節過長，
> 跟 §16.9 三視圖工作流是這一輪 SKILL.md 瘦身的兩個主要抽出對象）

## 前置知識

真空改變了打光的第一原理：**沒有介質 → 天空不是光源**。背景亮度不是「打光」的結果，是
World 底色本身；星點只是前景的亮點。配方＝`PRESETS["space"]`，工具＝`assets/space_lib.py`
＋`auto_space_fill()`／`assert_disc_in_frame()`／`request_world_hook()`／
`audit_horizon_surfaces()`／`audit_horizon_line()`（**不含** `setup_lens_flare()`——太空版
不使用，見下方規則 8）。

## 硬性規則

1. **World 底色壓到 `1e-5` 級**（`bg_color`）：AgX 會把 1e-3 級（實測 0.0035）抬成一層固定
   灰幕（量測整片天空固定停在 54.7/255、`std=0`），星點對比會被那層灰幕整片吃掉。掛上星空
   環境貼圖後這個值只扮演「沒掛貼圖時的天光底」。
2. **地面必須留在場景裡，但真空場景不能讓它入鏡**：`main()` 無條件 `build_ground()`，且
   `audit_floating()` 要拿地面當支撐面——**刪掉地面物件會讓 ray_cast 失去支撐面**，所以正解
   不是「不建」，是 `T.set_ground_void()`：per-object ray visibility 讓地面對相機與鏡面
   （glossy/transmission）不可見、`visible_diffuse`／`visible_shadow` 保持 True（仍提供接觸
   陰影），幾何照樣在場。要連陰影都不要（純真空構圖）用 `set_ground_void(alpha=0.0)` 走全透明
   材質版。**為什麼非做不可**：只要地面看得見，太陽掠射時它會在畫面下緣變成一條**平直的
   亮灰帶**，把雲狀銀河帶硬生生切斷（實測該處亮達 85/255、比銀河帶本身還亮），鏡面物件還會
   把那塊灰板反射進畫面——這是「星空被一條直線裁斷」最常見的成因，鏡頭怎麼調都躲不掉。
   **不要**用「配色壓到近黑」代替：近黑只讓它變暗，那條直線還在（近黑配色只適用於「仍想要
   一塊看得見的地」的構圖）。**連帶**：`PRESETS["space"]` 仍必須帶 `ground_a`／`ground_b`——
   `build_ground()` 是硬下標，缺鍵會直接 KeyError。**還有一個連帶**：真空場景的物件本來就
   沒有東西撐著，`audit_floating()` 會把每一件主體都回報成懸空（實測太空測試場景 2/2 件，
   `SCENE_STATE.auto_geometry_audit.floating`）——這是**預期的**，不要為了消這個警告去加底座
   （那會製造規則 11 的假地平線）；要消就用 `T.mark_side_attached(obj)` 把該批物件排除出懸空
   審查（該函式語意是「非重力式支撐」，在真空裡對所有主體都成立）。
3. **唯一主光是 SUN，柔化旋鈕是 `angle` 不是 `shadow_soft_size`**（後者在 SUN 上預設 0.0，
   根本不是柔化用的）。仰角別低於 10°，否則鏡面物件的受光面會縮成一條邊；方位仍要與相機同側
   （見一般曝光規範的太陽方位規則）。
4. **三點式一律 0**：真空沒有介質散射、沒有大氣、沒有地面反彈，棚拍三點式在太空沒有物理
   來源。要補的只有兩盞極弱來源——`auto_space_fill()` 的「冷藍行星反照（從下方來）」＋
   「暖色輪廓」，能量常數（3.0）刻意比 `auto_night_fill()`（16）再低一個量級，隨 bbox diag²
   縮放。
5. **曝光帶放寬，不是把燈加亮**：黑底佔畫面絕大多數，全畫面 mean 天然就低。
   `PRESETS["space"]` 的帶是 `(1.0, 45.0)`、`dark_max` 98%。**品質改看「主體可見像素比」**
   （`audit_framing()` 的 `coverage` ＋ 日盤/亮點是否存在）——加亮只會污染校準基準。
6. **星空兩層制，而且要依投影類型分流**：**點狀星一律用真幾何**（`make_star_points()`）——
   環境貼圖在**正交相機**下 mip 選擇退化，點狀星被糊成均勻灰（同一張貼圖：PERSP 空景最亮
   218、ORTHO 場景變常數 45.7，`dark_pct` 85.5%→0%）。環境貼圖只負責**低頻銀河帶**
   （`make_star_map()`）；PERSP 場景兩者疊加最好（貼圖給大面積輝光、幾何給銳利星點），ORTHO
   場景只信幾何星點。**銀河帶亮度極易失控**：實測 `band_glow=0.06` + `band_width_deg=14` 會
   把整張畫面洗成均勻灰（p50 由 8 跳到 29、`dark_pct` 55%→4%）；`band_glow≈0.035` +
   `band_width_deg≈7` 才是「一條看得出來的帶、其餘仍全黑」。
   **銀河帶的明暗塊必須是「平滑低頻雜訊」**（`space_lib._smooth_noise()` 的雙線性升採樣），
   **不可**用 `np.repeat` 把粗網格放大成 16×16 常數方塊——那在 equirect 貼圖上等於
   2.8° 的硬邊方格，鋪在大面積天空上、再被鏡面物件反射，就是肉眼一眼可見的方格棋盤
   （實測方塊版相鄰像素跳變率 5.5e-3、平滑版 1.8e-5，差 305 倍）。
   **貼圖只畫低頻帶，不畫點狀星**（`star_count=0` 是預設）：貼圖上的星斑只是固定幾個 texel
   的亮塊，天空一大片被放大後讀成方點。`install_star_world()` 另明確指定
   `interpolation="Linear"`（Closest 會把 texel 放大成硬邊方塊）。
   **星點球的細分級數 ≥2**（預設 2＝80 面）：icosphere 1 級只有 20 面，星點在畫面上
   拉到 5–7 px 時投影成多邊形剪影，肉眼直接讀成「一顆小方塊」；`size_range` 上限也應
   壓在約 4 px（1920 寬、420m 球殼 → `size ≤ 0.45m`）以內。全部實例共用同一份 mesh，
   升級細分只增加那一份的面數。
   **等距長方貼圖的 u（經度）方向必須環狀連續**：貼圖左右緣在球面上是同一條經線，粗網格的
   內插要讓最後一欄接回第一欄（`_smooth_noise()` 的 `xs` 取到 `cells_x`、索引取模）。否則
   u=0/1 會留下一個跳變——實測帶內那一欄平均跳 4.18/255、最大 10/255，而正常相鄰欄梯度只有
   0.28/255（差 15 倍），鋪到天上就是**一條把銀河帶垂直切斷的硬邊**。`space_lib --selftest`
   的 `equirect_seamless` 檢查在守這一條。
   **銀河帶取景也要自動避開硬邊**：帶被「看得見的地平線」或畫面上下緣切斷，是星空構圖最常見的
   醜畫面。`make_star_map(band_center_deg="auto")` 會依相機自動算中心仰角（`auto_band_center()`：
   掃出畫面涵蓋的仰角範圍、扣掉帶半寬 `k·σ`，地面看得見時再抬到地平線之上），呼叫端不需要自己
   猜數字；產生後用 `SP.audit_band_framing()` 驗——**地面可見、帶下緣低於地平線、且地平線處
   殘留帶亮度 >5% 峰值＝blocking**（`hard=True` 直接 exit 1），帶超出畫面上下緣只列 note
   （大尺度雲狀帶在特寫鏡頭被框邊裁切本來就自然）。**前提是它拿得到相機**：`band_center_deg="auto"`
   與 `audit_band_framing()` 都必須在 `build_camera()` 之後執行，標準做法是走
   `T.request_world_hook()`（`main()` 已把那支掛勾排在 `build_camera()` 之後，正是為了這個）。
7. **日盤＝只給相機看的自發光球**（`make_sun_disc()`）：太陽本身不會入鏡（直視＝過曝白板），
   要放一顆球當日盤，per-object ray visibility **只留 `camera`**、其餘 `diffuse`/`glossy`/
   `transmission`/`shadow`/`volume_scatter` 全關——開著 diffuse/glossy 會讓它變成第二顆太陽
   （照亮場景、投影），開著 shadow 會讓鏡面物件在反光裡留下不該有的陰影。視直徑 0.85° 是
   校準值（1.15° 會暈成饅頭）；`distance` 不影響畫面大小，但要確認相機 `clip_end > distance`
   （`build_camera()` 給 `max(1000, 對焦距離×4)`，300m 內安全）。**擺好一律呼叫
   `assert_disc_in_frame()`**（`hard=True`）——日盤是視覺錨點，沒入鏡＝這張圖沒有太陽。
8. **太空正式版不啟用鏡頭光暈**：`setup_lens_flare()` 的鬼影鏈在真空的高對比、低亮度背景上
   讀成髒點與塊狀物，成效為負——太空場景**不要呼叫** `request_lens_flare()`。函式本身仍保留
   給其他題材（夜間街景、賽博龐克），參數與 5.1 落差見 SKILL.md §8 Glare 節點條目：門檻要夾
   在星點峰值與日盤亮度之間（實測 40–60，太低＝數千光斑淹沒畫面）。若其他題材要用，**必須走
   `request_lens_flare()`**，不能直接在 `subject_fn()` 裡呼叫 `setup_lens_flare()`——
   `scene.compositing_node_group` 一次只掛一個 group，`setup_render()` 會把它整個蓋掉
   （`main()` 在 `setup_render()` 之後才執行這個請求）。
9. **鏡面物件的反光只在太陽位於相機背後時看得到**（鏡面反射的是相機背後那半個天球）。想同時
   要「日盤入鏡」與「鏡面把太陽反射進畫面」在光學上互斥——一張圖選一個：日盤入鏡的構圖，
   鏡面反射到的會是星空；要驗鏡面反射太陽，就把相機移到太陽的反側（逆光構圖，實測鉻球會
   出現一圈熾亮的鏡面高光）。
10. **星空環境貼圖要走 `request_world_hook()`**：World 是 `build_world()` 在 `main()` 裡建的
    （而且它會 `bpy.data.worlds.new()` 整個換掉），在 `subject_fn()` 期間先接上的貼圖會被直接
    蓋掉。
11. **不要用水平平台撐物件，也不要讓任何朝上平面以掠射角入鏡**（假地平線＝星空被一條橫線
    切斷的主因）：底座的頂面只要幾乎與視線平行，就會把太陽打成一條平直亮邊——實測亮度跳躍
    36/255、橫向連續 46% 畫面寬，比星雲帶本身亮十幾倍，肉眼直接讀成地平線。**真空裡懸空是
    物理正確的**，所以正解是不要那個面（物件直接浮在星空前），不是把它壓黑。**材質處理
    無效**：掠射角的 Fresnel 反射率對任何材質都趨近 1，實測換成 base 0.03／roughness 0.8 的
    暗霧面烤漆、並關掉全部補光之後，同一道亮邊仍有 20–23/255 的跳躍（變因實驗：把底座隱藏
    → 事件消失；只關補光 → 事件照樣出現，證明成因是那個面本身）。真要保留這個面只有兩條路：
    把它的 `Specular IOR Level` 設 0（連 Fresnel 一起關掉），或改變機位不再以掠射角看它。
    **兩道審查在守這一條**：`T.audit_horizon_surfaces()`（渲染前、幾何層——找「朝上 + 掠射角
    入鏡 + 水平跨度 ≥15% 畫面寬」的面）與 `T.audit_horizon_line()`（渲染後、像素層——抓畫面裡
    任何亮度跳躍 ≥20/255 且橫向連續 ≥22% 的亮邊）；`main()` 在 `PRESET == "space"` 時**兩道
    都自動跑**，分別寫進 `SCENE_STATE.auto_geometry_audit.horizon_surfaces` 與
    `SCENE_STATE.horizon_audit`。跟 `set_ground_void()` 的分工：那支只管名為 `Ground` 的地面，
    **主體自帶的底座不在它的守備範圍**，要靠這兩道。

## 落地 checklist（Stage B 動工前逐條核對）

`PRESETS["space"]` ｜ `bg_color` 1e-5 級 ｜ **地面不入鏡**（`T.set_ground_void()`；地面物件
仍留在場景裡當支撐面）｜ **主體不要有水平底座／朝上平台**（`T.audit_horizon_surfaces()`
渲染前跑一次，見規則 11）｜ 三點式 0 ＋ `auto_space_fill()` ｜ `make_star_points()`（PERSP
才加 `make_star_map(band_center_deg="auto")`，走 `request_world_hook()`）｜
`SP.audit_band_framing(hard=True)`（帶被看得見的地平線切斷＝exit 1）｜
`T.audit_horizon_line()`（渲染後，橫向亮邊 ≥20/255 × ≥22% 寬＝列 issue）｜ `make_sun_disc()`
＋ `assert_disc_in_frame(hard=True)` ｜ **不呼叫** `request_lens_flare()` ｜ 相機
`clip_end > 日盤距離` ｜ 曝光只看「帶內 ＋ 主體可見像素比」。

## 驗證方式

**校準基準（本機實測，1920×1080 Cycles/AgX）**：主鏡（28mm、日盤入鏡＋銀河帶＋900 顆幾何星、
無光暈、無底座）mean 6.8／p50 3.0／`dark_pct` 73.2%／`clipped_pct` 0.03%；逆光特寫（35mm
鉻球）mean 5.6／p50 1.0／`dark_pct` 78.5%／`clipped_pct` 0.04%。兩張的最大橫向亮度跳躍
≤8/255（底座版本是 36/255，`audit_horizon_line()` 當場攔下），亮點數千級——星點是「數百個
孤立亮點」而不是一片亮斑，這是太空場景在數值上該長的樣子。端到端腳本範例：
`.capybala/test-scripts/space_test.py`。

## 常見錯誤（實戰回填區）

| # | 錯誤 | 判讀方式 | 修正 |
|---|---|---|---|
| 1 | 地面物件直接刪除，而不是用 `set_ground_void()` | `audit_floating()` 失去支撐面，`ray_cast` 相關審查報錯 | 地面留在場景裡，只用 `set_ground_void()` 讓它對相機/鏡面不可見 |
| 2 | 為了消除 `audit_floating()` 的懸空警告而幫主體加底座 | 底座頂面掠射角入鏡，變成假地平線把星空切斷 | 用 `T.mark_side_attached(obj)` 把主體排除出懸空審查，不要加底座 |
| 3 | 銀河帶 `band_glow`/`band_width_deg` 沿用一般夜景數值 | 整張畫面洗成均勻灰 | 太空場景銀河帶用 `band_glow≈0.035`／`band_width_deg≈7`，不是任意值 |
| 4 | 星空環境貼圖在 `subject_fn()` 期間直接掛上 `Background.Color` | `main()` 的 `build_world()` 之後把 World 整個換掉，貼圖被蓋掉 | 一律走 `T.request_world_hook()` |
