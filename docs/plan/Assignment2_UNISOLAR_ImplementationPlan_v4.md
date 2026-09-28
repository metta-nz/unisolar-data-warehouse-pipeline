# COMP8812 Assignment 2 — Kế hoạch triển khai v4 (UNISOLAR + AWS S3)

Cập nhật: 28/09/2026. Phiên bản này thay thế các plan trước (Plan A PVOutput/AWS, Plan B UNISOLAR thuần SQL Server).

---

## 0. Các mốc cố định (theo đề + bài giảng 19/09)

| Mốc | Nội dung |
|---|---|
| Thứ Sáu 9/10 (đêm) | Hạn nộp báo cáo lên link Turnitin chính thức. Chỉ nộp **bản cuối**. Nộp nháp sẽ báo 100% trùng lặp và bị trừ điểm. |
| Đêm trước ngày trình bày | Nộp slide (Chủ nhật trình bày thì nộp tối thứ Bảy). |
| Thứ Bảy 10/10 và Chủ nhật 11/10 | Trình bày. Phải có mặt cả hai ngày, dù đã trình bày xong. |
| Slot | Có vẻ là **10 phút** (cô nói "10 minutes" khi xếp lịch), khác với file đề (20 + 10 phút). **Cần xác nhận với cô.** |

Nộp trễ: trừ 10%/20%/30% cho mỗi 24h, quá 72h là không chấm.

**Ba điều cần hỏi cô bằng email (một lần):**
1. Thời lượng trình bày thực tế (10 phút hay 20 + 10).
2. Chính sách Gen AI: bản cam kết trong file đề cấm "for any purpose", còn cô nói miệng là dùng được nhưng phải viết lại của mình.
3. Độ dài: file đề ghi 5.000 từ gồm cả bảng, hình, refs, phụ lục; cô nói miệng mơ hồ 6.000–7.000.

---

## 1. Tổng quan giải pháp

**Đề tài:** Data warehouse cho phân tích sản lượng điện mặt trời của La Trobe University (5 campus, 42 site PV), tích hợp dữ liệu thô CSV (UNISOLAR) với dữ liệu JSON bán cấu trúc từ NASA POWER, lưu trữ theo tầng trên AWS S3, mô hình Star Schema, phân tích mô tả/chẩn đoán bằng Power BI.

**Bối cảnh kinh doanh (Introduction):** La Trobe cam kết Net Zero Carbon Emissions vào 2029 và xây nền tảng LEAP (AI/phân tích dữ liệu điện, khí, nước). Người ra quyết định là ban quản lý năng lượng/bền vững của trường. Bài toán: site nào đang hoạt động tốt/kém, khi nào và vì sao sản lượng thay đổi, dữ liệu có đủ tin cậy để ra quyết định không.

**Phạm vi phân tích (theo lời cô):** chỉ **mô tả** (mean, median, min, max, range, SD) và **chẩn đoán** (drill-down giải thích nguyên nhân) kèm trực quan hóa. **Không** làm dự báo/ML.

---

## 2. Bộ dữ liệu và nguồn (dán vào báo cáo)

### 2.1 Nguồn chính: UNISOLAR (CSV, có sẵn)
- Kaggle: https://www.kaggle.com/datasets/cdaclab/unisolar
- GitHub: https://github.com/CDAC-lab/UNISOLAR
- Bài báo (trích IEEE): S. Wimalaratne, D. Haputhanthri, S. Kahawala, G. Gamage, D. Alahakoon, A. Jennings, "UNISOLAR: An Open Dataset of Photovoltaic Solar Energy Generation in a Large Multi-Campus University Setting," 2022 15th Int. Conf. on Human System Interaction (HSI), 2022, pp. 1–5, doi: 10.1109/HSI55341.2022.9869474. (IEEE: https://ieeexplore.ieee.org/document/9869474/)
- Giấy phép: CC BY-NC-SA 4.0, chỉ dùng học thuật/phi thương mại, phải ghi nguồn.
- Phạm vi: 42 site PV, 5 campus (Bundoora, Bendigo, Albury-Wodonga, Mildura, Shepparton), 01/2020 – 04/2022, sản lượng 15 phút.
- File đang dùng:
  - `Solar_Energy_Generation.csv` (~2,73 triệu dòng, 15 phút, khóa SiteKey)
  - `Weather_Data_reordered_all.csv` (~372 nghìn dòng, 15 phút, khóa CampusKey)
  - `Solar_Site_Details.csv` (42 dòng metadata site)
  - `Monthly_Summary_Solar.csv` (dùng để đối chiếu kết quả ETL)
- **Chỉ dùng cột có thật trong file.** Không dùng các cột lấy từ plan ngoài: `Module_Temp_C`, `TiltAngle`, `BuildingName`, `CommissionDate`, `ClimateZone`.
- Trích dẫn bản Kaggle của `cdaclab` và bài IEEE, không trích các bản sao của người khác.

### 2.2 Nguồn bán cấu trúc: NASA POWER (JSON) — cần chốt sau bước kiểm tra cột
- Tài liệu: https://power.larc.nasa.gov/docs/services/api/temporal/ (API giờ theo điểm, hỗ trợ JSON).
- Cấu trúc JSON lồng nhau (`properties → parameter → {tham số → {timestamp: giá trị}}`), phù hợp để trình bày bước flatten.
- Lưu ý kỹ thuật: tối đa 15 tham số/truy vấn; múi giờ mặc định LST nên yêu cầu UTC rồi đổi sang giờ Melbourne; dữ liệu từ vệ tinh/tái phân tích, độ phân giải thô (một giá trị cho cả campus), nên phải nêu trong Limitations.
- Phương án dự phòng: Open-Meteo (https://open-meteo.com/, CC BY 4.0, phải ghi nguồn, JSON dạng mảng song song, có sẵn biến mây).
- **Điểm chốt (Ngày 1):** chạy `df.columns` cho hai file CSV. Nếu file thời tiết đã có bức xạ, JSON chỉ dùng để bổ sung/đối chiếu (mây, khuếch tán, trực xạ) và ghi rõ điều đó trong báo cáo.
- Ghi vào báo cáo: đúng số truy vấn, khoảng thời gian, tọa độ 5 campus, ngày tải, tham số đã chọn.

### 2.3 Không dùng (ghi trong Discussion như hướng mở rộng)
- UNICON (tiêu thụ điện 2018–2021, cùng nhóm tác giả, https://www.kaggle.com/datasets/cdaclab/unicon): chồng lấn 2020–2021, cho phép hỏi "điện mặt trời đáp ứng bao nhiêu nhu cầu", nhưng cần ghép meter–campus, quá rủi ro với 7 ngày.

---

## 3. Kiến trúc pipeline trên AWS S3

```
[Kaggle CSV + NASA POWER JSON]
        │  (Python: tải về, không sửa)
        ▼
 S3  raw/        ── dữ liệu thô nguyên bản + manifest (số dòng, kích thước, checksum, ngày tải)
        │  (Python: tải từ S3 về, profiling, DQ rules, inject lỗi, làm sạch)
        ▼
 S3  clean/      ── dữ liệu đã làm sạch
 S3  dq_log/     ── DQLog (mọi dòng vi phạm/sửa)
        │  (Python: dựng dim + fact, surrogate key)
        ▼
 S3  curated/    ── dimSite, dimCampus, dimTime, fact (Parquet)
        │  (Python/SQLAlchemy hoặc BULK INSERT)
        ▼
 SQL Server (DW chính)  ──►  Power BI Desktop
```

**Việc cần làm trên S3:**
- Tạo bucket với 5 prefix: `raw/`, `clean/`, `dq_log/`, `curated/`, `logs/`. Chọn region gần (ví dụ ap-southeast-2).
- IAM user quyền tối thiểu chỉ cho bucket này, không dùng root; bật Block Public Access; không hardcode key (dùng `aws configure` hoặc biến môi trường); đặt budget alert.
- Bật versioning trên `raw/`, và một lifecycle rule (chuyển lớp lưu trữ rẻ hơn sau N ngày) để trả lời câu hỏi về bảo vệ/lưu giữ dữ liệu thô.
- Mỗi lần chạy ghi một dòng log vào `logs/`: nguồn, thời điểm, số dòng, kích thước.
- Script điều phối `run_pipeline.py` chạy tuần tự ingest → clean → curate và in **số dòng ở từng tầng** (raw → clean → curated → SQL Server).
- Đọc file lớn (2,7 triệu dòng) theo chunk hoặc dùng Parquet để tránh hết RAM.

**Athena/Glue: chỉ làm nếu còn dư thời gian sau Ngày 4** (tạo bảng ngoài trên `curated/` để đối chiếu số dòng với SQL Server). Không dùng Lambda/Step Functions/Redshift/EC2, chỉ nêu trong Discussion.

**Ba ý trả lời "vì sao S3":** tách lưu trữ khỏi tính toán; giữ dữ liệu thô bất biến để tái xử lý và truy vết; chi phí thấp khi dữ liệu lớn.

---

## 4. Thiết kế Star Schema (v3, giữ nguyên, có bổ sung)

**Fact:** `factSolarGeneration`, grain = **1 site × 15 phút**, khóa thay thế BIGINT.
- Measures gốc: sản lượng, các chỉ số thời tiết/bức xạ (cột thật trong file).
- Measures tính toán: `Performance_Ratio`, `Expected_Yield_kWh`, `Revenue_Saved_AUD`, `CO2_Offset_KG`.
- `Revenue_Saved_AUD` và `CO2_Offset_KG` chỉ tính khi có nguồn chính thức cho biểu giá (theo `TariffPeriod`) và hệ số phát thải. Nếu không kịp, bỏ hai measure này, không hardcode.

**Dimensions:**
- `dimSite` (42 dòng, đã denormalise thuộc tính campus để tránh Snowflake).
- `dimTime` gồm `Season` (Nam bán cầu) và `TariffPeriod` (Peak/Shoulder/Off-Peak của Victoria).
- Nếu cần, `dimCampus` hoặc giữ campus trong `dimSite` (nhất quán với v3).

**Rủi ro đã biết (bắt buộc ghi ở phần Limitations):**
- Thời tiết ở grain campus được gán xuống grain site. Campus 1 có 27 site nên các phép AVG thời tiết bị lệch (trùng lặp).
  Cách xử lý: tính AVG thời tiết trên tập (campus, thời điểm) đã khử trùng bằng view SQL hoặc measure DAX, và giải thích trong báo cáo.
- Dữ liệu JSON theo giờ, sản lượng theo 15 phút: **không** dùng `inner join` theo timestamp (sẽ mất ~75% dòng). Gán giá trị giờ cho 4 khoảng 15 phút của giờ đó (forward-fill có ghi chú), hoặc tổng hợp sản lượng về giờ. Chọn một cách, ghi rõ trong báo cáo.
- Múi giờ/DST: chuẩn hóa mọi timestamp về cùng một múi giờ (UTC, hoặc Australia/Melbourne) ngay ở bước làm sạch.
- Ghi chú lý thuyết (có thể bị hỏi): chỉ năng lượng là additive; công suất, nhiệt độ, bức xạ là non-additive nên dùng AVG.

---

## 5. Quy tắc DQA (tối thiểu 4; bản v3 có 5) và DQLog

| # | Chiều DQ | Quy tắc | Xử lý |
|---|---|---|---|
| 1 | Completeness | Phân biệt null ban đêm (hợp lệ) và null ban ngày (bất thường) trong sản lượng (~56% null tổng, phần lớn ban đêm) | Ban đêm: giữ nguyên/ghi nhận. Ban ngày: flag, không nội suy, không gán `-1`. |
| 2 | Consistency | Liên tục timestamp 15 phút theo từng site | Đếm khoảng trống, flag. |
| 3 | Validity | Số tấm pin phải là số nguyên (SiteKey 16 và 27 bất thường) | Sửa hoặc flag, ghi log. |
| 4 | Consistency | Chuẩn hóa các dạng thiếu giá trị ("TBD" vs NaN) | Đưa về một biểu diễn. |
| 5 | Validity | Bức xạ nằm trong giới hạn vật lý 0–1361 W/m² | Reject/flag vi phạm. |

**Bắt buộc theo cô (bài giảng 19/09):** nếu một rule không có vi phạm tự nhiên, phải **tự inject lỗi** (null, giá trị âm, trùng lặp, định dạng ngày lộn xộn), chạy rule, và cho thấy số dòng bị bắt. Trong báo cáo ghi rõ đó là lỗi chèn có kiểm soát. Không được nói "dữ liệu sạch nên không có rule".

**Ban đêm:** dùng bức xạ hoặc góc cao mặt trời, không dùng khung giờ cố định (Victoria thay đổi theo mùa).

**Cấu trúc DQLog** (lưu tại `s3://…/dq_log/`): `log_id`, `run_id`, `source_file`, `row_ref`, `site_key`, `timestamp`, `rule_id`, `dq_dimension`, `column_name`, `violated_value`, `severity`, `action_taken` (Reject/Fix/Flag), `logged_at`.

**Bảng tổng kết bắt buộc (DQ Summary):** N_raw → số dòng vi phạm theo từng Rule → N_clean, cộng bảng số dòng theo từng tầng (raw/clean/curated/SQL Server) để chứng minh không mất dòng.

**Trích dẫn cho DQ:** cô nhấn mạnh phải trích nguồn ngay cả ý tưởng quy tắc chất lượng (ví dụ Wang & Strong 1996 cho các chiều DQ, DAMA-DMBOK, Kimball). Bạn tự kiểm chứng nguồn trước khi đưa vào refs.

---

## 6. Bộ câu hỏi kinh doanh và phân tích (Power BI, 4–5 visual)

| # | Câu hỏi | Phân tích | Visual |
|---|---|---|---|
| 1 | Campus/site nào hiệu quả nhất và kém nhất trên mỗi đơn vị công suất? | Mô tả (mean, median, range, SD) | Bar + map |
| 2 | Sản lượng theo giờ và mùa? Giờ nắng cao điểm, mùa yếu? | Mô tả | Line / heatmap |
| 3 | Bức xạ, nhiệt độ, mây giải thích bao nhiêu biến động sản lượng? | Chẩn đoán (tương quan, **không kết luận nhân quả**) | Scatter + drill-down |
| 4 | Site nào lệch khỏi nhóm ngang hàng (nghi lỗi thiết bị)? | Chẩn đoán (outlier) | Box/outlier |
| 5 | Site nào thiếu/gián đoạn dữ liệu nhiều, ảnh hưởng độ tin cậy KPI ra sao? | Mô tả từ DQLog | Bar theo site |

Power BI: có map và slicer; các visual thuộc loại phân tích khác nhau. Boxplot cần custom visual; kiểm tra sớm. Power BI Desktop chỉ chạy trên Windows, cần sẵn máy để demo. Dashboard kết nối SQL Server (không nối Athena để tránh lỗi ODBC khi demo).
Thận trọng: 2,3 năm dữ liệu chưa đủ để kết luận "suy giảm" (degradation).
Công thức: PR trung bình phải dùng `SUM(sản lượng)/SUM(sản lượng kỳ vọng)`, không dùng trung bình các tỷ lệ; không tính PR ban đêm là 0.

---

## 7. Lịch 7 ngày (28/9 → 4/10), viết báo cáo chiếm phần lớn thời gian

Nguyên tắc: **cuối mỗi ngày kỹ thuật dành 1,5–2 giờ viết ngay phần tương ứng** khi bằng chứng còn mới. Ngày 5 và 6 gần như dành trọn cho viết. Thời gian dưới đây là gợi ý; điều chỉnh theo lịch thật của bạn.

| Ngày | Kỹ thuật | Viết báo cáo |
|---|---|---|
| **1 · T2 28/9** | Tạo S3 bucket + IAM + prefix; upload `raw/` (CSV) kèm manifest. Chạy `df.columns` cả hai file, profiling, lập data dictionary. **Chốt nguồn JSON** và tải JSON cho 5 campus, upload `raw/`. Chụp: cấu trúc bucket, code upload, mẫu CSV/JSON. | Section 1 (Intro) ~350 từ + khung Section 2 (Dataset). |
| **2 · T3 29/9** | ETL: tải từ S3, flatten JSON (NASA POWER), chuẩn hóa múi giờ, quyết định cách gán giờ → 15 phút. Ghi kết quả staging. Profiling chi tiết để chọn rule dựa trên lỗi thật. | Hoàn thiện Section 2 (~450). Nháp Section 3 (kiến trúc S3 + ETL). |
| **3 · T4 30/9** | 4–5 DQ rules + inject lỗi + DQLog + bảng đếm dòng trước/sau; ghi `clean/` và `dq_log/` lên S3. Chụp: code rule, DQLog, DQ Summary. | Section 4 (Cleaning, ~900) nháp đầy đủ. |
| **4 · T5 1/10** | Dựng dim/fact → `curated/` (Parquet) → nạp SQL Server. Vẽ Star Schema trên dbdiagram.io, chụp DDL. Đối chiếu với `Monthly_Summary_Solar.csv`. Viết các câu SQL phân tích. (Athena chỉ nếu còn dư giờ.) | Hoàn thiện Section 3 (~1.000). |
| **5 · T6 2/10** | Power BI 4–5 visual (bố cục một buổi sáng), chụp ảnh nền sáng, to. Kiểm tra số liệu Power BI khớp SQL. | **Cả ngày:** Section 5 (Exploring, ~1.100). |
| **6 · T7 3/10** | Chỉ sửa lỗi kỹ thuật nếu có. | **Cả ngày:** Section 6 (Results/Conclusion/Discussion, ~700), refs, caption, bảng; đọc lại toàn bài, cắt về đúng 5.000 từ. |
| **7 · CN 4/10** | Chuẩn bị máy demo (S3 console, Jupyter/script, SQL Server, `.pbix`). | Viết lại giọng cá nhân (đọc to từng đoạn). Làm **slide 8–10 trang** (ảnh to, ít chữ) và luyện 10 phút. |

**Đệm 5/10 → 9/10:** chạy kiểm tra similarity bằng link cô cung cấp (link này chỉ hiện mức trùng lặp, **không** hiện chỉ số AI); sửa lần cuối; nộp báo cáo đêm 9/10. Luyện thuyết trình, chuẩn bị câu hỏi phản biện.

---

## 8. Cấu trúc báo cáo và phân bổ từ (tổng 5.000, gồm cả bảng/hình/refs)

| Section | Điểm | Từ | Nội dung chính |
|---|---|---|---|
| 1. Introduction / Motivation | 5 | ~350 | Net Zero 2029, LEAP, bài toán cho người ra quyết định, kết quả kỳ vọng |
| 2. Dataset / Data collected | 5 | ~450 | UNISOLAR + JSON: nguồn, link, quy mô, giấy phép, mẫu dữ liệu, công sức chuyển đổi |
| 3. Data extraction & processing | 15 | ~1.000 | Kiến trúc S3 (raw/clean/curated), Python/boto3, flatten JSON, Star Schema, SQL Server; bằng chứng code |
| 4. Cleaning of raw data | 12 | ~900 | 4–5 rules, DQLog, inject lỗi, bảng đếm dòng, thách thức khi làm sạch |
| 5. Exploring & analysing | 15 | ~1.100 | 4–5 phân tích, thống kê mô tả, outlier, diễn giải cho quyết định |
| 6. Results, conclusion, discussion | (thuộc mục chất lượng 13) | ~700 | Khuyến nghị kinh doanh, hạn chế (broadcast grain, NASA POWER thô, 2,3 năm dữ liệu), hướng mở rộng (UNICON, Athena) |
| References + caption/bảng | 5 (2,5 refs + 2,5 format) | ~500 | ≥ 6 refs IEEE, có trích dẫn trong bài |

Định dạng: Calibri 11pt, single spacing, normal margins. Nếu tiếp tục dùng LaTeX như Assignment 1, dùng Carlito (tương thích Calibri), 11pt, lề chuẩn. British English.

**Nguyên tắc viết (quan trọng vì cô chạy kiểm tra AI/similarity):**
- Viết từ kết quả thật của mình: số dòng, ảnh chụp, bảng, lỗi gặp phải. Đoạn dựa trên trải nghiệm cá nhân là đoạn khó bị trùng nhất.
- Lập dàn ý bằng gạch đầu dòng số liệu trước, rồi viết thành câu bằng lời của mình. Đọc to lại từng đoạn.
- Không dán văn bản do AI tạo. Cô đã nói rõ AI-generated indicator sẽ hiện ở phía cô và có thể bị trừ nặng.
- Mọi ý mượn (DQ dimensions, Star Schema, định nghĩa) đều phải có trích dẫn.
- Mục tiêu similarity ≤ 10–12% (ngưỡng cô: < 15%).

---

## 9. Bằng chứng cần chụp (ảnh to, nền sáng, cho cả báo cáo và slide)

1. Cấu trúc bucket trên S3 Console (raw/clean/dq_log/curated/logs).
2. Code `boto3` upload/download + manifest số dòng.
3. Mẫu CSV thô và JSON thô (lồng nhau), rồi bảng sau khi flatten.
4. Data dictionary.
5. Code ETL (đọc, chuẩn hóa múi giờ, gán giờ → 15 phút).
6. Code từng DQ rule + đoạn inject lỗi.
7. Bảng DQLog (mẫu dòng) và DQ Summary (trước/sau, theo rule).
8. Bảng số dòng theo tầng (raw → clean → curated → SQL Server).
9. Sơ đồ Star Schema (dbdiagram.io) + SQL DDL.
10. Kết quả đối chiếu với `Monthly_Summary_Solar.csv`.
11. Các câu SQL phân tích + kết quả.
12. 4–5 visual Power BI (chụp từ cửa sổ Power BI thật, không dùng ảnh AI).

---

## 10. Slide (8–10 trang, nộp đêm trước ngày trình bày)

Cô chấm nhanh bằng slide, nên mỗi phần cần **một câu giải thích + bằng chứng lớn**, không nhiều chữ.

| Slide | Nội dung |
|---|---|
| 1 | Intro/Motivation: Net Zero 2029, bài toán, câu hỏi kinh doanh |
| 2 | Dataset: vì sao chọn, nguồn/link, quy mô, giấy phép, JSON bổ sung |
| 3 | Kiến trúc pipeline (S3 raw/clean/curated → SQL Server → Power BI) + chụp bucket |
| 4 | Extraction & Star Schema (sơ đồ + code chính) |
| 5 | Cleaning: các rule + DQLog + bảng đếm dòng (kèm ảnh inject lỗi và kết quả) |
| 6 | Cleaning (tiếp) hoặc thử thách khi làm sạch |
| 7–8 | Phân tích: 2–3 visual đáng chú ý, mỗi cái gắn với một quyết định |
| 9 | Kết luận + khuyến nghị kinh doanh |
| 10 | Hạn chế + hướng mở rộng |

Đúng phân bổ đề: Dataset/extraction 3–4 slide, Cleaning 1–2, EDA 2–3, Conclusion 2, Intro 1–2.

**Tiêu chí điểm trình bày (30):** Focus 2,5; Visual 2,5; Elocution 5; Time 2,5; **Technical 12,5**; **Questions 5**. Tức 17,5/30 là kiến thức và trả lời câu hỏi. Cô ưu tiên hiểu bức tranh tổng thể hơn chi tiết vụn.

---

## 11. Danh sách câu hỏi phản biện cần chuẩn bị

1. Grain của fact table là gì? Vì sao chọn grain đó?
2. Vì sao Star chứ không phải Snowflake/Constellation? Vì sao denormalise campus vào `dimSite`?
3. Vì sao weather ở grain campus gán xuống site làm lệch AVG, và bạn xử lý thế nào?
4. Vì sao không nội suy hoặc gán `-1` cho sản lượng thiếu? (null ban đêm là hợp lệ)
5. Từng DQ rule bắt được bao nhiêu dòng? Bao nhiêu là lỗi chèn, bao nhiêu là lỗi tự nhiên?
6. Vì sao lưu trên S3 mà không lưu local? Vì sao tách raw/clean/curated?
7. JSON được flatten như thế nào? Vì sao chọn NASA POWER và hạn chế của nó là gì?
8. Ghép dữ liệu 15 phút với dữ liệu theo giờ như thế nào? Có mất dòng không? Chứng minh bằng số liệu.
9. Tương quan giữa bức xạ và sản lượng có phải nhân quả không?
10. Phân tích của bạn giúp ai ra quyết định gì?
11. Nếu dữ liệu lớn gấp 100 lần thì thay đổi gì? (Spark/Athena, phân vùng theo ngày/site)
12. Vì sao dùng SQL Server làm DW chính chứ không dùng Athena?

---

## 12. Rủi ro và cách giảm

| Rủi ro | Giảm thiểu |
|---|---|
| Chi phí/khóa AWS bị lộ | IAM tối thiểu, budget alert, không commit key |
| Mất 75% dòng khi merge 15 phút với giờ | Gán giờ → 15 phút hoặc gộp về giờ; in số dòng ở mọi bước |
| Lệch múi giờ/DST | Chuẩn hóa timestamp sớm, kiểm tra với vài mốc thủ công |
| Rule không có vi phạm | Inject lỗi có kiểm soát, ghi rõ trong báo cáo |
| Không có Power BI/Windows | Xác nhận máy ngay Ngày 1 |
| Dồn viết vào cuối | Viết từng section sau mỗi bước kỹ thuật |
| Trễ nộp | Nộp trước 9/10, không nộp bản nháp lên link chính thức |
| Trùng lặp/AI indicator cao | Viết từ kết quả thật, đọc to, kiểm tra similarity bằng link cô đưa |

---

## 13. Checklist cuối trước khi nộp

- [ ] Có đủ nguồn (link Kaggle, GitHub, DOI IEEE, tài liệu NASA POWER) và ghi giấy phép.
- [ ] Dữ liệu thô nằm ở `s3://…/raw/`, không bị sửa.
- [ ] `clean/`, `dq_log/`, `curated/` có dữ liệu, số dòng ở mọi tầng khớp với báo cáo.
- [ ] ≥ 4 DQ rules có bằng chứng code, DQLog, DQ Summary, số dòng trước/sau; nêu rõ phần lỗi chèn.
- [ ] Star Schema có sơ đồ, DDL, đối chiếu `Monthly_Summary_Solar.csv`.
- [ ] ≥ 4 phân tích khác nhau, trực quan hóa từ dữ liệu thật; không dùng ảnh AI.
- [ ] Mọi câu diễn giải tương quan không kết luận nhân quả.
- [ ] Báo cáo ≤ 5.000 từ (tính cả bảng, hình, refs), Calibri 11pt, single spacing, normal margins.
- [ ] ≥ 6 refs IEEE, có trích dẫn trong bài; mọi nguồn đã kiểm chứng.
- [ ] Similarity đã kiểm bằng link cô cung cấp; bài do bạn tự viết.
- [ ] Slide 8–10 trang, ảnh to nền sáng, nộp đêm trước ngày trình bày.
- [ ] Máy demo mở sẵn S3 console, script, SQL Server, `.pbix`.
- [ ] Đã đăng ký tên vào ngày trình bày (10/10 hoặc 11/10) và có mặt cả hai ngày.
