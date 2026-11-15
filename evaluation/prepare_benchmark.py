"""Author source-grounded labels, freeze disjoint evidence families before scoring.

This module is evaluation data, never imported by the serving pipeline. Evidence
must exist verbatim in the real PDF-derived index, at the annotated physical page.
"""

import argparse
import json
from pathlib import Path

from src import config
from src.build_index import file_sha256
from src.retriever import Retriever

DIRECT = [
    ("D01", "Trường Đại học Sư phạm Thành phố Hồ Chí Minh thành lập ngày nào?", [(4, "thành lập ngày 27/10/1976 theo Quyết định số 426-TTg")]),
    ("D02", "Triết lý giáo dục của Trường đặt ai ở vị trí trung tâm?", [(5, "hướng đến người học – nhân vật trung tâm của hoạt động giáo dục.")]),
    ("D03", "Theo quy chế đại học, một tín chỉ lý thuyết gồm bao nhiêu giờ trên lớp và tự học?", [(8, "15 giờ học lý thuyết và 30 giờ tự học, chuẩn bị cá nhân có hướng dẫn")]),
    ("D04", "Ở trình độ đại học, học phần tiên quyết phải được tích lũy khi nào?", [(9, "Học phần tiên quyết: là học phần sinh viên phải tích lũy trước khi học các học phần khác có liên quan;")]),
    ("D05", "Theo quy chế đào tạo đại học, một lớp sinh viên có tối đa bao nhiêu sinh viên?", [(14, "Mỗi lớp có không quá 50 sinh viên;")]),
    ("D06", "Sinh viên đại học chính quy tự đăng ký học phần từ học kỳ nào?", [(15, "Từ học kỳ thứ hai của khóa học, sinh viên phải tự đăng ký các học phần trên hệ thống đăng ký học tập của Trường theo kế hoạch được ban hành.")]),
    ("D07", "Sinh viên đại học học lại để cải thiện điểm thì lần điểm nào là chính thức?", [(19, "Sinh viên có điểm học phần đạt, được đăng ký học lại chính học phần đó để cải thiện điểm, điểm lần học cuối là điểm chính thức của học phần.")]),
    ("D08", "Ngưỡng điểm trung bình học kỳ dẫn đến cảnh báo học tập của sinh viên đại học chính quy là bao nhiêu?", [(21, "Điểm trung bình học kỳ đạt dưới 0,8 đối với học kỳ đầu của khóa học, dưới 1,0 đối với các học kỳ tiếp theo;")]),
    ("D09", "Sinh viên đại học chính quy bị cảnh báo học tập bao nhiêu lần thì thuộc diện buộc thôi học?", [(22, "Bị cảnh báo học tập 03 lần liên tiếp trong một khóa học;"), (22, "Bị cảnh báo học tập đến lần thứ tư tính từ đầu khóa;")]),
    ("D10", "Nghỉ học tạm thời vì nhu cầu cá nhân có tính vào thời gian học chính thức của sinh viên đại học không?", [(25, "Thời gian nghỉ học tạm thời vì nhu cầu cá nhân được tính vào thời gian học tập chính thức")]),
    ("D11", "Sinh viên đại học sớm nhất được đăng ký chương trình thứ hai khi nào?", [(28, "Sinh viên được đăng ký học chương trình thứ hai sớm nhất khi đã được xếp trình độ năm thứ hai của chương trình thứ nhất.")]),
    ("D12", "Sinh viên cao đẳng Giáo dục Mầm non chính quy bắt đầu tự đăng ký học phần từ học kỳ nào?", [(40, "Từ học kỳ thứ hai của khóa học, sinh viên phải tự đăng ký các học phần trên hệ thống đăng ký học tập của Trường theo kế hoạch được ban hành.")]),
    ("D13", "Sinh viên có nghĩa vụ gì về học phí và bảo hiểm y tế?", [(60, "Đóng học phí, bảo hiểm y tế đầy đủ và đúng thời hạn.")]),
    ("D14", "Điều kiện học tập, rèn luyện, kỷ luật và số tín chỉ thông thường để xét học bổng khuyến khích học tập là gì?", [(72, "Trong học kỳ, sinh viên có kết quả học tập, rèn luyện từ loại khá trở lên, không bị kỷ luật từ mức khiển trách trở lên"), (72, "Tổng số tín chỉ sinh viên tích lũy trong một học kỳ phải lớn hơn hoặc bằng 15 tín chỉ theo kế hoạch trong CTĐT của khóa học")]),
    ("D15", "Học bổng khuyến khích học tập được cấp bao nhiêu tháng trong năm học?", [(73, "HBKKHT được cấp theo từng học kỳ chính và cấp 10 tháng trong năm học.")]),
    ("D16", "Trường phải báo địa phương và gia đình khi sinh viên bị kỷ luật ở những mức nào?", [(81, "Trường hợp sinh viên bị kỷ luật mức đình chỉ học tập có thời hạn hoặc buộc thôi học, Trường gửi thông báo cho địa phương và gia đình sinh viên biết")]),
    ("D17", "Cố vấn học tập được hưởng chế độ và bố trí thời gian công tác như thế nào?", [(87, "Được hưởng các chế độ theo Quy chế chi tiêu nội bộ và bố trí thời gian thực hiện công tác CVHT theo quy định chế độ làm việc của giảng viên.")]),
    ("D18", "Điểm rèn luyện được đánh giá trên thang điểm bao nhiêu?", [(92, "Điểm rèn luyện được đánh giá bằng thang điểm 100.")]),
    ("D19", "Sinh viên không tự đánh giá kết quả rèn luyện thì nhận kết quả gì?", [(95, "Sinh viên không thực hiện tự đánh giá kết quả rèn luyện theo quy định sẽ nhận điểm 0 và xếp loại rèn luyện kém (xét theo từng học kỳ).")]),
    ("D20", "Sinh viên khiếu nại điểm rèn luyện ở đâu và trong thời hạn bao lâu?", [(99, "Sinh viên gửi đơn khiếu nại về Phòng CTCT&HSSV trong vòng 07 ngày kể từ ngày công bố kết quả điểm rèn luyện đã được Hội đồng cấp Trường thông qua.")]),
    ("D21", "Sinh viên đại học bị rèn luyện yếu hoặc kém hai học kỳ liên tiếp bị xử lý thế nào, kể cả khi lặp lại lần thứ hai?", [(99, "Sinh viên trình độ đại học bị xếp loại rèn luyện yếu, kém trong hai học kỳ liên tiếp thì phải tạm ngừng học ít nhất một học kỳ ở học kỳ tiếp theo và nếu bị xếp loại rèn luyện yếu, kém hai học kỳ liên tiếp lần thứ hai thì sẽ bị buộc thôi học.")]),
    ("D22", "Sinh viên cao đẳng sư phạm có rèn luyện kém cả năm và lặp lại lần hai bị xử lý thế nào?", [(99, "Sinh viên trình độ cao đẳng sư phạm bị xếp loại rèn luyện kém trong cả năm học thì phải tạm ngừng học một năm học ở năm học tiếp theo và nếu bị xếp loại rèn luyện kém cả năm lần thứ hai thì sẽ bị buộc thôi học.")]),
    ("D23", "Bài kiểm tra ngoại ngữ đầu vào gồm những kỹ năng nào và theo cấu trúc trình độ nào?", [(110, "Bài kiểm tra trình độ ngoại ngữ đầu vào gồm kỹ năng nghe và kỹ năng đọc được xây dựng dựa trên cấu trúc đề thi tương đương trình độ bậc 3/6.")]),
    ("D24", "Chuẩn đầu ra ngoại ngữ tối thiểu của sinh viên đại học thuộc Điều 1 quy định ngoại ngữ là bậc nào?", [(111, "Sinh viên theo quy định Điều 1 tốt nghiệp trình độ đại học phải đạt tối thiểu bậc 3/6 theo Khung năng lực ngoại ngữ 6 bậc dùng cho Việt Nam hoặc tương đương để được công nhận tốt nghiệp.")]),
    ("D25", "Sinh viên ngoại trú được Trường hỗ trợ việc đăng ký ngoại trú không?", [(117, "được Trường và các bên liên quan hỗ trợ và giúp đỡ trong việc đăng ký ngoại trú.")]),
    ("D26", "Nguồn ngân sách Nhà nước cho nghiên cứu khoa học sinh viên được trích từ kinh phí nào?", [(123, "Ngân sách Nhà nước trích từ kinh phí hoạt động khoa học và công nghệ.")]),
    ("D27", "Mỗi sinh viên có thể tham gia và chịu trách nhiệm chính bao nhiêu đề tài nghiên cứu khoa học trong một năm học?", [(130, "Mỗi sinh viên có thể tham gia nhiều đề tài, chịu trách nhiệm chính thực hiện một đề tài NCKH trong một năm học;")]),
    ("D28", "Trang phục của người học trong giờ học tại Trường cần đáp ứng yêu cầu gì?", [(137, "trang phục của người học phải gọn gàng, lịch sự, kín đáo, phù hợp với thuần phong mỹ tục, môi trường giáo dục, bảo đảm nghiêm túc, thẩm mỹ.")]),
    ("D29", "Quy tắc trách nhiệm khi ứng xử trên mạng xã hội yêu cầu điều gì?", [(139, "Chịu trách nhiệm về các hành vi, ứng xử trên mạng xã hội; phối hợp với các cơ quan chức năng để xử lý hành vi, nội dung thông tin vi phạm pháp luật.")]),
    ("D30", "Theo nghị định được in trong sổ tay, mức hỗ trợ chi phí sinh hoạt hằng tháng cho sinh viên sư phạm là bao nhiêu?", [(144, "Sinh viên sư phạm được Nhà nước hỗ trợ 3,63 triệu đồng/tháng để chi trả chi phí sinh hoạt trong thời gian học tập tại trường.")]),
    ("D31", "Thời gian hỗ trợ học phí và chi phí sinh hoạt cho sinh viên sư phạm tối đa bao nhiêu tháng mỗi năm học?", [(144, "Thời gian hỗ trợ tiền đóng học phí và chi phí sinh hoạt được xác định theo số tháng thực tế học tập tại trường theo quy định, nhưng không quá 10 tháng/năm học.")]),
    ("D32", "Sau bao lâu kể từ quyết định công nhận tốt nghiệp mà sinh viên sư phạm hưởng hỗ trợ không công tác trong ngành giáo dục thì thuộc diện bồi hoàn?", [(145, "Sinh viên sư phạm đã hưởng chính sách không công tác trong ngành giáo dục sau 02 năm kể từ ngày có quyết định công nhận tốt nghiệp;")]),
    ("D33", "Ký túc xá tiếp nhận hồ sơ đăng ký nội trú ở đâu và khi nào?", [(170, "Viên chức thuộc Ban Quản lý KTX được phân công tiếp nhận hồ sơ trong thời hạn được thông báo chính thức tại Văn phòng KTX.")]),
    ("D34", "Theo sổ tay, email liên hệ Phòng Công nghệ Thông tin là gì?", [(173, "Email : phongcntt@hcmue.edu.vn")]),
    ("D35", "Theo sổ tay, email Phòng Công tác chính trị và Học sinh, sinh viên là gì?", [(173, "Email : hopthusinhvien@hcmue.edu.vn")]),
    ("D36", "Theo sổ tay, email và website của Thư viện là gì?", [(178, "Email : thuvien@hcmue.edu.vn Website : lib.hcmue.edu.vn")]),
    ("D37", "Theo sổ tay, văn phòng Ký túc xá ở địa chỉ nào?", [(180, "351A Lạc Long Quân, Phường 5, Quận 11, TP. HCM.")]),
    ("D38", "Chương trình quốc tế song ngành 2+2 Ngôn ngữ Trung Quốc và Giáo dục Hán ngữ Quốc tế có cơ hội nghề nghiệp gì tại doanh nghiệp sử dụng tiếng Trung?", [(198, "Người học sau khi tốt nghiệp có thể làm biên – phiên dịch, trợ lý, thương mại,… tại các cơ quan nhà nước, doanh nghiệp trong nước và nước ngoài có sử dụng tiếng Trung Quốc;")]),
    ("D39", "Theo danh sách trong sổ tay, Bảo tàng Chứng tích Chiến tranh ở địa chỉ nào?", [(210, "Bảo tàng Chứng tích Chiến tranh Số 28 Võ Văn Tần, Phường 6, Quận 3")]),
    ("D40", "Ngành Tâm lý học giáo dục có cơ hội làm chuyên viên tâm lý học đường ở đâu?", [(201, "Chuyên viên tâm lý học đường thực hiện công tác dự phòng tâm lý (giảng dạy kỹ năng sống và các chuyên đề Tâm lý học giáo dục có liên quan, sàng lọc các vấn đề sức khỏe tâm thần, tư vấn – tham vấn học đường) tại các trường phổ thông và cơ sở giáo dục nghề nghiệp;")]),
]

PARAPHRASES = [
    ("P01", "Em học đại học chính quy, mới vào thì khi nào phải tự chọn môn trên hệ thống?", ["D06"]),
    ("P02", "Đại học chính quy mà điểm học kỳ thấp cỡ nào thì bị cảnh báo vậy?", ["D08"]),
    ("P03", "Đại học chính quy bị cảnh báo mấy lần thì bị đuổi học?", ["D09"]),
    ("P04", "Em học đại học, bảo lưu vì việc riêng có làm tốn thời gian được phép học không?", ["D10"]),
    ("P05", "Muốn có học bổng khuyến khích thì điểm học, điểm rèn luyện, nợ kỷ luật và số tín chỉ cần ra sao?", ["D14"]),
    ("P06", "Đại học mà rèn luyện yếu hai kỳ liền rồi tái diễn lần nữa thì có bị đuổi không?", ["D21"]),
    ("P07", "Sinh viên đại học thuộc diện áp dụng quy định ngoại ngữ cần ngoại ngữ cỡ nào mới ra trường?", ["D24"]),
    ("P08", "Em ở trọ ngoài trường, nhà trường có giúp đăng ký ngoại trú không?", ["D25"]),
    ("P09", "Theo sổ tay, học sư phạm được Nhà nước cho bao nhiêu tiền sinh hoạt mỗi tháng?", ["D30"]),
    ("P10", "Trong sổ tay, muốn gửi mail cho phòng CNTT thì gửi địa chỉ nào?", ["D34"]),
]

COMPOSITE = [
    ("C01", "Theo quy chế đại học, so sánh số giờ học và tự học của một tín chỉ lý thuyết với một tín chỉ thực hành.", ["D03"], [(8, "30 giờ thực hành, thí nghiệm, thảo luận và 15 giờ tự học, chuẩn bị cá nhân có hướng dẫn")]),
    ("C02", "Đại học chính quy: học kỳ đầu do ai xếp lịch và từ kỳ nào sinh viên phải tự đăng ký?", ["D06"], [(15, "Trong học kỳ đầu tiên của khóa học, sinh viên học tập theo thời khóa biểu do Trường ấn định")]),
    ("C03", "Đại học chính quy có ngưỡng điểm học kỳ cảnh báo nào và cảnh báo lặp lại bao nhiêu lần dẫn đến buộc thôi học?", ["D08", "D09"], []),
    ("C04", "Tổng hợp điều kiện học tập, rèn luyện, kỷ luật, số tín chỉ xét học bổng khuyến khích và số tháng được cấp trong năm học.", ["D14", "D15"], []),
    ("C05", "Sinh viên có nghĩa vụ đóng học phí, bảo hiểm thế nào và nếu bỏ tự đánh giá rèn luyện thì hậu quả gì?", ["D13", "D19"], []),
    ("C06", "So sánh cách xử lý kết quả rèn luyện yếu, kém của sinh viên đại học với rèn luyện kém của sinh viên cao đẳng sư phạm, gồm cả tái diễn lần hai.", ["D21", "D22"], []),
    ("C07", "Bài kiểm tra ngoại ngữ đầu vào kiểm tra kỹ năng gì và chuẩn đầu ra tối thiểu cho sinh viên đại học thuộc Điều 1 quy định ngoại ngữ là gì?", ["D23", "D24"], []),
    ("C08", "Theo sổ tay, cho tôi email của Phòng Công nghệ Thông tin và Phòng Công tác chính trị và Học sinh, sinh viên.", ["D34", "D35"], []),
    ("C09", "Theo nghị định trong sổ tay, sinh viên sư phạm được hỗ trợ sinh hoạt bao nhiêu mỗi tháng và tối đa mấy tháng mỗi năm học?", ["D30", "D31"], []),
    ("C10", "Theo sổ tay, email và website Thư viện là gì, đồng thời văn phòng Ký túc xá ở đâu?", ["D36", "D37"], []),
]

UNANSWERABLE = [
    ("U01", "Điểm chuẩn trúng tuyển ngành Sư phạm Toán năm 2026 chính xác là bao nhiêu?", "Sổ tay không có điểm trúng tuyển năm 2026."),
    ("U02", "Học phí chính xác một tín chỉ ngành Tâm lý học năm học 2026–2027 là bao nhiêu đồng?", "Không có bảng mức thu học phí của năm học 2026–2027."),
    ("U03", "Mã sinh viên của tôi là 50.01.101.999, GPA cá nhân hiện tại là bao nhiêu?", "Không có hồ sơ điểm của cá nhân."),
    ("U04", "Ngày mai ở Thành phố Hồ Chí Minh có mưa lúc 8 giờ không?", "PDF không cung cấp dự báo thời tiết."),
    ("U05", "Cho tôi mật khẩu email sinh viên của bạn Nguyễn Văn An.", "PDF không có mật khẩu tài khoản cá nhân."),
    ("U06", "Số chỗ ký túc xá còn trống ngay hôm nay là bao nhiêu?", "Không có dữ liệu chỗ trống theo thời gian thực."),
    ("U07", "Giá vé máy bay từ Thành phố Hồ Chí Minh ra Hà Nội ngày mai là bao nhiêu?", "Không có giá vé máy bay."),
]

PARTIAL = [
    ("U08", "Theo nghị định trong sổ tay, mức hỗ trợ sinh hoạt cho sinh viên sư phạm là bao nhiêu mỗi tháng và tiền của cá nhân tôi tháng 11/2026 đã chuyển chưa?", ["D30"], "Không có trạng thái chuyển tiền của cá nhân tháng 11/2026."),
    ("U09", "Theo sổ tay, địa chỉ văn phòng Ký túc xá ở đâu và hôm nay còn chính xác bao nhiêu giường trống?", ["D37"], "Không có số giường trống hôm nay."),
    ("U10", "Email Phòng Công nghệ Thông tin trong sổ tay là gì và mật khẩu email sinh viên của tôi là gì?", ["D34"], "Không có mật khẩu cá nhân."),
]


def build_benchmark(index):
    def evidence(page, quote):
        matches = [c for c in index.chunks if c["page"] == page and quote in c["text"]]
        if not matches:
            raise ValueError(f"Chứng cứ không tồn tại tại trang {page}: {quote}")
        return {"source": index.meta["source"], "page": page, "quote": quote,
                "gold_chunk_ids": [c["chunk_id"] for c in matches]}

    rows = []
    for identifier, question, references in DIRECT:
        rows.append(dict(id=identifier, question=question, category="direct", answerability="full",
                         split="dev" if int(identifier[1:]) <= 20 else "test", evidence_families=[identifier],
                         evidence=[evidence(*ref) for ref in references], missing_information=[]))
    direct = {row["id"]: row for row in rows}
    for category, items in (("paraphrase", PARAPHRASES), ("composite", COMPOSITE)):
        for item in items:
            identifier, question, families = item[:3]
            extra = item[3] if len(item) > 3 else []
            splits = {direct[family]["split"] for family in families}
            if len(splits) != 1:
                raise ValueError("Một nhóm chứng cứ bị rò rỉ giữa dev/test")
            rows.append(dict(id=identifier, question=question, category=category, answerability="full",
                             split=splits.pop(), evidence_families=families,
                             evidence=[ref for family in families for ref in direct[family]["evidence"]]
                                      + [evidence(*ref) for ref in extra], missing_information=[]))
    for identifier, question, reason in UNANSWERABLE:
        rows.append(dict(id=identifier, question=question, category="unanswerable", answerability="none",
                         split="dev" if int(identifier[1:]) <= 5 else "test", evidence_families=[identifier],
                         evidence=[], missing_information=[reason]))
    for identifier, question, families, reason in PARTIAL:
        rows.append(dict(id=identifier, question=question, category="unanswerable", answerability="partial",
                         split="test", evidence_families=families,
                         evidence=[ref for family in families for ref in direct[family]["evidence"]],
                         missing_information=[reason]))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=config.PROJECT_ROOT / "evaluation" / "benchmark")
    args = parser.parse_args()
    if any((args.out / name).exists() for name in ("dev.json", "test.json", "manifest.json")):
        parser.error("Benchmark đã đóng băng. Chọn thư mục mới để tạo phiên bản nhãn mới.")
    index = Retriever(config.INDEX_DIR)
    rows = build_benchmark(index)
    args.out.mkdir(parents=True, exist_ok=True)
    for split in ("dev", "test"):
        (args.out / f"{split}.json").write_text(json.dumps([row for row in rows if row["split"] == split], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = dict(version=1, source_sha256=index.meta["source_sha256"], chunks_sha256=index.meta["chunks_sha256"],
                    counts={category: sum(row["category"] == category for row in rows)
                            for category in ("direct", "paraphrase", "composite", "unanswerable")},
                    files={f"{split}.json": file_sha256(args.out / f"{split}.json") for split in ("dev", "test")},
                    label_notes="Authored from actual PDF-derived chunks. Split by evidence family; not an independently authored benchmark. Freeze before final evaluation. Unanswerable absence labels require human review.")
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
