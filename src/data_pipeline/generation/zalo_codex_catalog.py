"""Static, locally authored Zalo social-engineering scenario catalog.

The catalog deliberately stores semantic roots rather than cosmetic prompts.
Each root names the relationship, impersonated persona, pretext, manipulation
mechanism, requested action, and likely consequence that define one lineage.
The five direct-message renderings live in dedicated static catalog modules.
They are new semantic reconstructions authored locally from each root, not
claimed recoveries of wording that never existed. Variants of one lineage
therefore always share one seed identifier when finalized by
:mod:`zalo_codex_recovery`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.data_pipeline.generation.zalo_direct_actions import DIRECT_ACTIONS
from src.data_pipeline.generation.zalo_direct_messages import DIRECT_MESSAGE_TEMPLATES


CATALOG_VERSION = "zalo-codex-direct-2026-08-17"
SEED_NAMESPACE_VERSION = "zalo-codex-2026-08-08"
AUTHORING_RUNTIME = "gpt-5.6-sol-codex-session"


@dataclass(frozen=True, slots=True)
class ScenarioRoot:
    """One independently motivated Zalo social-engineering lineage."""

    anchor: str
    relationship: str
    persona: str
    pretext: str
    mechanism: str
    requested_action: str
    consequence: str
    urgency: str

    @property
    def semantic_signature(self) -> tuple[str, ...]:
        return (
            self.relationship.casefold(),
            self.persona.casefold(),
            self.pretext.casefold(),
            self.mechanism.casefold(),
            self.requested_action.casefold(),
            self.consequence.casefold(),
        )


SCENARIO_ROOTS: tuple[ScenarioRoot, ...] = (
    ScenarioRoot("family-hospital-deposit", "Con trai của người nhận vừa được đưa vào khoa cấp cứu", "bác sĩ trực cấp cứu", "Bệnh viện cần tạm ứng trước khi phẫu thuật", "cuộc gọi video chỉ hiện khuôn mặt vài giây rồi mất tiếng", "quét mã QR cá nhân để chuyển tiền viện phí", "mất tiền vào tài khoản cá nhân không thuộc bệnh viện", "Phải hoàn tất trong mười phút"),
    ScenarioRoot("friend-stolen-wallet-loan", "Một người bạn thân nói vừa bị móc mất ví", "người bạn dùng tài khoản Zalo dự phòng", "Bạn cần tiền mặt để về nhà", "ảnh đại diện và cách xưng hô được sao chép từ tài khoản thật", "chuyển khoản khoản vay ngắn hạn vào số tài khoản lạ", "mất tiền cho kẻ chiếm đoạt danh tính", "Đừng gọi số cũ vì điện thoại đang bị giữ"),
    ScenarioRoot("sibling-roadside-rescue", "Em trai nói xe bị tai nạn trên đường tỉnh", "nhân viên cứu hộ đi cùng em trai", "Xe phải nộp phí kéo về gara", "người gửi phát một đoạn ghi âm giọng giống người thân", "đặt cọc phí cứu hộ qua ví điện tử", "mất tiền cho dịch vụ cứu hộ giả", "Xe cứu hộ sẽ bỏ đi nếu chậm thanh toán"),
    ScenarioRoot("classmate-wedding-gift", "Lớp trưởng cũ đang gom quà cưới cho bạn cùng lớp", "lớp trưởng của nhóm cựu học sinh", "Danh sách đóng góp sắp được chốt", "tài khoản mới tham gia nhóm và dùng ảnh lớp trưởng", "gửi tiền mừng vào mã QR được ghim trong nhóm", "tiền đóng góp bị chuyển cho người giả mạo", "Chốt danh sách trước tối nay"),
    ScenarioRoot("funeral-committee-contribution", "Gia đình một đồng nghiệp được báo là vừa có tang", "đại diện công đoàn cơ quan", "Công đoàn đang thu tiền phúng viếng", "kẻ gửi tạo nhóm Zalo mang tên cơ quan và thêm nhiều số lạ", "chuyển tiền phúng viếng vào tài khoản ban tổ chức", "mất tiền và làm lộ danh sách đồng nghiệp", "Đoàn viếng sẽ xuất phát trong một giờ nữa"),
    ScenarioRoot("teacher-fieldtrip-fee", "Phụ huynh được báo lớp của con đổi lịch tham quan", "giáo viên chủ nhiệm", "Nhà trường cần thu bổ sung phí xe và bảo hiểm", "tài khoản dùng đúng ảnh cô giáo nhưng số điện thoại mới", "nộp phí chuyến đi qua mã QR cá nhân", "mất học phí vào tài khoản không thuộc nhà trường", "Danh sách học sinh sẽ khóa lúc mười bảy giờ"),
    ScenarioRoot("principal-scholarship-processing", "Học sinh được thông báo trúng học bổng đột xuất", "hiệu trưởng nhà trường", "Hồ sơ học bổng cần phí xác minh tài khoản", "văn bản có logo trường được gửi dưới dạng ảnh mờ", "chuyển phí xử lý để nhận học bổng", "mất phí và lộ thông tin học sinh", "Suất học bổng sẽ chuyển cho người khác nếu phản hồi muộn"),
    ScenarioRoot("landlord-rent-account-change", "Người thuê nhận tin chủ nhà đã đổi tài khoản nhận tiền", "chủ nhà đang công tác xa", "Tiền thuê tháng này phải chuyển sang tài khoản của kế toán", "tài khoản giả biết đúng địa chỉ căn hộ và ngày đóng tiền", "chuyển toàn bộ tiền thuê vào tài khoản mới", "mất khoản tiền thuê và vẫn còn nghĩa vụ với chủ thật", "Không gọi vì chủ nhà đang họp ở nước ngoài"),
    ScenarioRoot("apartment-fire-registration", "Cư dân được yêu cầu cập nhật danh sách phòng cháy", "trưởng ban quản lý chung cư", "Mỗi căn hộ phải kích hoạt thẻ kiểm tra an toàn", "một biểu mẫu Zalo giả hiển thị logo ban quản lý", "mở biểu mẫu và nhập căn cước cùng ảnh khuôn mặt", "bị đánh cắp danh tính cư dân", "Căn hộ không đăng ký sẽ bị cắt thẻ ra vào ngày mai"),
    ScenarioRoot("ceo-supplier-transfer", "Kế toán nhận lệnh kín từ người tự nhận là tổng giám đốc", "tổng giám đốc doanh nghiệp", "Nhà cung cấp mới cần được ứng tiền để giữ hợp đồng", "người gửi yêu cầu giữ bí mật và không qua quy trình phê duyệt", "chuyển gấp tiền công ty vào tài khoản nhà cung cấp mới", "thất thoát quỹ doanh nghiệp", "Hợp đồng sẽ mất hiệu lực trong ba mươi phút"),
    ScenarioRoot("hr-payroll-verification", "Nhân viên được báo hồ sơ lương bị lỗi", "chuyên viên nhân sự", "Phòng nhân sự cần xác minh lại tài khoản nhận lương", "tệp biểu mẫu giả yêu cầu đăng nhập bằng tài khoản công ty", "điền mật khẩu email và thông tin ngân hàng vào biểu mẫu", "mất tài khoản công việc và dữ liệu lương", "Lương tháng này sẽ bị treo nếu không cập nhật"),
    ScenarioRoot("it-remote-support", "Nhân viên được báo máy tính đang phát tán mã độc", "kỹ thuật viên công nghệ thông tin", "Thiết bị phải được kiểm tra từ xa", "người gửi dùng thuật ngữ nội bộ rồi đề nghị cài công cụ điều khiển", "cài ứng dụng điều khiển màn hình và đọc mã kết nối", "máy tính bị chiếm quyền điều khiển", "Hệ thống sẽ khóa tài khoản trong mười lăm phút"),
    ScenarioRoot("coworker-zalo-login-qr", "Đồng nghiệp nói cần đăng nhập Zalo trên máy họp", "đồng nghiệp cùng dự án", "Nhóm dự án sắp có cuộc gọi khẩn", "ảnh chụp mã QR đăng nhập được gửi kèm lời nhờ quét hộ", "quét mã QR đăng nhập Zalo trên thiết bị lạ", "tài khoản Zalo của nạn nhân bị chiếm", "Cuộc họp bắt đầu ngay bây giờ"),
    ScenarioRoot("recruiter-background-check", "Ứng viên được báo đã qua vòng phỏng vấn", "chuyên viên tuyển dụng", "Doanh nghiệp cần chứng thư kiểm tra lý lịch", "hợp đồng giả được gửi từ tài khoản Zalo cá nhân", "nộp phí thẩm tra hồ sơ tuyển dụng", "mất phí và giấy tờ định danh", "Vị trí sẽ bị hủy nếu chưa nộp trong hôm nay"),
    ScenarioRoot("freelance-escrow-activation", "Người làm tự do nhận được dự án giá trị cao", "khách hàng doanh nghiệp", "Khoản thanh toán đang nằm trong tài khoản ký quỹ", "ảnh số dư giả được dùng để tạo niềm tin", "đóng phí kích hoạt để mở khóa tiền ký quỹ", "mất phí mà không nhận được dự án", "Khách hàng sẽ chuyển việc cho người khác sau một giờ"),
    ScenarioRoot("courier-address-correction", "Người nhận được báo bưu kiện ghi sai địa chỉ", "nhân viên bưu cục", "Đơn hàng cần cập nhật tuyến giao", "kẻ gửi biết tên người nhận từ nhãn vận chuyển bị lộ", "thanh toán phí sửa địa chỉ qua đường dẫn rút gọn", "mất thông tin thẻ và phí giả", "Bưu kiện sẽ bị hoàn kho cuối ngày"),
    ScenarioRoot("delivery-refund-screen-share", "Khách hàng được báo đơn giao đồ ăn bị tính tiền hai lần", "nhân viên chăm sóc khách hàng giao đồ ăn", "Hệ thống cần hoàn lại giao dịch trùng", "người gửi hướng dẫn chia sẻ màn hình khi mở ứng dụng ngân hàng", "bật chia sẻ màn hình và đọc mã xác nhận hoàn tiền", "tài khoản ngân hàng bị chiếm đoạt", "Phiên hoàn tiền chỉ còn hiệu lực năm phút"),
    ScenarioRoot("seller-escrow-release", "Người bán được báo đã có khách thanh toán", "quản trị viên sàn mua bán", "Tiền bán hàng đang bị giữ do tài khoản chưa xác minh", "trang giả hiển thị đơn hàng và số tiền chờ nhận", "đăng nhập ngân hàng qua liên kết để mở khóa tiền bán", "mất thông tin đăng nhập ngân hàng", "Đơn hàng sẽ tự hủy nếu không xác nhận"),
    ScenarioRoot("buyer-chargeback-otp", "Người mua bị dọa có khiếu nại hoàn tiền", "nhân viên xử lý tranh chấp của chợ trực tuyến", "Tài khoản cần chứng minh giao dịch do chính chủ thực hiện", "người gửi đọc đúng mã đơn hàng rồi xin mã xác thực", "gửi mã OTP để đóng hồ sơ khiếu nại", "giao dịch trái phép được xác nhận", "Tài khoản mua hàng sẽ bị khóa ngay"),
    ScenarioRoot("zalo-account-recovery", "Người dùng nhận cảnh báo tài khoản vừa bị đăng nhập nơi khác", "nhân viên Trung tâm hỗ trợ Zalo", "Phiên đăng nhập lạ cần được thu hồi", "tài khoản hỗ trợ giả gửi trang đăng nhập giống Zalo", "nhập số điện thoại và mật khẩu vào trang khôi phục", "tài khoản Zalo bị chiếm và dùng lừa danh bạ", "Liên hệ bạn bè sẽ bị xóa sau mười phút"),
    ScenarioRoot("zalo-verified-badge", "Chủ cửa hàng được mời nhận dấu xác minh", "chuyên viên Zalo Business", "Trang bán hàng đủ điều kiện lên tài khoản chính thức", "một giấy chứng nhận giả hứa tăng lượt tiếp cận", "trả phí cấp dấu xác minh qua tài khoản cá nhân", "mất phí và quyền quản trị trang", "Ưu đãi xác minh chỉ áp dụng trong hôm nay"),
    ScenarioRoot("zalo-community-strike", "Quản trị viên nhóm nhận thông báo nội dung bị tố cáo", "bộ phận tiêu chuẩn cộng đồng Zalo", "Nhóm có nguy cơ bị xóa vì vi phạm bản quyền", "liên kết kháng nghị dẫn tới trang đăng nhập giả", "đăng nhập để gửi đơn kháng nghị vi phạm", "thông tin quản trị nhóm bị đánh cắp", "Nhóm sẽ bị xóa sau sáu giờ"),
    ScenarioRoot("group-admin-vote", "Thành viên được báo nhóm cần bầu lại quản trị viên", "quản trị viên nhóm dân cư", "Kết quả biểu quyết phải gắn với tài khoản thật", "mã QR được giới thiệu là phiếu bầu nhưng thực chất là mã đăng nhập", "quét mã QR để xác nhận phiếu bầu", "tài khoản Zalo bị đăng nhập trên máy của kẻ gian", "Cuộc bỏ phiếu đóng sau mười phút"),
    ScenarioRoot("police-confidential-investigation", "Người nhận bị nêu tên trong một vụ rửa tiền", "điều tra viên công an", "Tài sản phải được kiểm tra bí mật", "người gửi cấm liên hệ gia đình và gửi ảnh thẻ ngành giả", "chuyển tiền vào tài khoản tạm giữ để chứng minh vô tội", "mất toàn bộ tiền vì lệnh tạm giữ giả", "Không được ngắt liên lạc cho đến khi xác minh xong"),
    ScenarioRoot("court-summons-apk", "Người nhận được báo có giấy triệu tập chưa ký nhận", "thư ký tòa án", "Hồ sơ tố tụng chỉ xem được qua ứng dụng chuyên dụng", "tệp cài đặt ngoài kho ứng dụng được gửi trong Zalo", "cài tệp ứng dụng để mở giấy triệu tập điện tử", "điện thoại nhiễm mã độc đánh cắp dữ liệu", "Vắng mặt sẽ bị xử lý theo thủ tục khẩn"),
    ScenarioRoot("tax-refund-app", "Người nộp thuế được báo có khoản hoàn thuế", "cán bộ cơ quan thuế", "Tài khoản thuế điện tử chưa liên kết ngân hàng", "ứng dụng giả yêu cầu quyền trợ năng để tự động đối soát", "cài ứng dụng hoàn thuế và cấp quyền trợ năng", "mã độc đọc tin nhắn và điều khiển giao dịch", "Khoản hoàn sẽ hết hạn trong ngày"),
    ScenarioRoot("ward-relief-registration", "Hộ gia đình được thông báo thuộc diện nhận trợ cấp", "cán bộ phường phụ trách an sinh", "Danh sách cứu trợ cần xác thực cư trú", "biểu mẫu giả thu ảnh căn cước và phí hồ sơ", "tải ảnh hai mặt căn cước và nộp phí đăng ký", "lộ danh tính và mất phí", "Danh sách sẽ khóa trước buổi phát quà"),
    ScenarioRoot("social-insurance-benefit", "Người lao động được báo còn khoản bảo hiểm chưa nhận", "nhân viên bảo hiểm xã hội", "Ứng dụng định danh cần được kích hoạt lại", "cuộc gọi Zalo hướng dẫn chia sẻ màn hình từng bước", "mở ứng dụng ngân hàng khi đang chia sẻ màn hình", "thông tin tài chính và mã xác thực bị lộ", "Hồ sơ sẽ bị trả về nếu thoát cuộc gọi"),
    ScenarioRoot("electricity-disconnection", "Chủ hộ được báo hóa đơn điện đang treo", "nhân viên điện lực khu vực", "Công tơ sẽ bị ngắt do lỗi đối soát", "người gửi dùng đúng mã khách hàng lấy từ hóa đơn cũ", "thanh toán hóa đơn vào mã QR không thuộc điện lực", "mất tiền nhưng hóa đơn thật vẫn chưa thanh toán", "Đội cắt điện đang trên đường tới"),
    ScenarioRoot("water-meter-replacement", "Cư dân được báo đồng hồ nước phải thay khẩn", "kỹ thuật viên công ty cấp nước", "Thiết bị cũ bị cho là không đạt kiểm định", "lịch hẹn giả được xác nhận bằng ảnh phiếu công tác", "đặt cọc chi phí thay đồng hồ nước", "mất tiền cọc cho kỹ thuật viên giả", "Nếu không đặt lịch hôm nay sẽ bị ngừng cấp nước"),
    ScenarioRoot("telecom-esim-migration", "Thuê bao được báo SIM vật lý sắp mất sóng", "nhân viên nhà mạng", "Số điện thoại phải chuyển gấp sang eSIM", "người gửi yêu cầu đọc mã xác thực với lý do kích hoạt", "cung cấp mã OTP đổi SIM cho nhân viên hỗ trợ", "số điện thoại bị chiếm để nhận mã ngân hàng", "SIM cũ sẽ bị vô hiệu trong mười lăm phút"),
    ScenarioRoot("doctor-imported-medicine", "Gia đình bệnh nhân được báo thuốc điều trị đã hết", "bác sĩ điều trị", "Một lô thuốc nhập khẩu hiếm vừa được giữ chỗ", "toa thuốc giả và ảnh hộp thuốc được gửi để tạo tin tưởng", "chuyển tiền mua thuốc vào tài khoản của người quen bác sĩ", "mất tiền và trì hoãn điều trị thật", "Nhà thuốc chỉ giữ thuốc đến cuối giờ"),
    ScenarioRoot("pharmacy-scarce-medicine", "Người mua hỏi thuốc hiếm cho người thân", "dược sĩ của nhà thuốc lớn", "Kho khác còn đúng một hộp thuốc", "tài khoản giả sao chép ảnh quầy thuốc và phản hồi đánh giá", "đặt cọc toàn bộ tiền thuốc trước khi giao", "mất tiền cọc và không nhận được thuốc", "Có khách khác đang chờ thanh toán"),
    ScenarioRoot("insurance-claim-inspection", "Người được bảo hiểm nhận tin hồ sơ bồi thường đã duyệt", "giám định viên bảo hiểm", "Khoản bồi thường cần chứng nhận hiện trường bổ sung", "một hóa đơn dịch vụ giám định giả được gửi kèm", "nộp phí giám định để giải ngân bồi thường", "mất phí và lộ dữ liệu hồ sơ tai nạn", "Hồ sơ sẽ đóng nếu không bổ sung trong ngày"),
    ScenarioRoot("charity-beneficiary-transfer", "Nhà hảo tâm được mời hỗ trợ trực tiếp một gia đình khó khăn", "điều phối viên quỹ từ thiện", "Quỹ nói hệ thống quyên góp đang bảo trì", "ảnh bệnh án và thư cảm ơn cũ được tái sử dụng", "chuyển tiền cứu trợ vào tài khoản cá nhân của điều phối viên", "tiền từ thiện bị chiếm đoạt", "Gia đình cần đóng viện phí ngay tối nay"),
    ScenarioRoot("pet-adoption-transport", "Người nhận nuôi được báo thú cưng đã sẵn sàng chuyển đi", "tình nguyện viên trạm cứu hộ", "Đơn vị vận chuyển yêu cầu mua lồng chuyên dụng", "video con vật bị lấy từ trang khác để tạo niềm tin", "thanh toán phí vận chuyển và tiền thuê lồng", "mất tiền cho ca nhận nuôi không tồn tại", "Xe chở thú cưng sắp rời trạm"),
    ScenarioRoot("travel-ticket-reissue", "Khách du lịch được báo vé máy bay bị hủy chặng", "nhân viên đại lý du lịch", "Hãng yêu cầu trả chênh lệch để đổi vé", "mã đặt chỗ thật bị dùng kèm đường dẫn thanh toán giả", "trả phí đổi vé vào cổng thanh toán gửi qua Zalo", "mất tiền và thông tin thẻ", "Giá giữ chỗ chỉ còn hiệu lực hai mươi phút"),
    ScenarioRoot("hotel-relocation-deposit", "Khách được báo khách sạn đã hết phòng do sự cố", "quản lý khách sạn", "Khách sạn đối tác cần tiền cọc mới", "ảnh xác nhận đặt phòng cũ được chỉnh sửa", "chuyển thêm tiền cọc để giữ phòng thay thế", "mất tiền cọc và không có chỗ ở", "Phòng cuối cùng sẽ được nhả sau mười phút"),
    ScenarioRoot("tour-group-emergency", "Thành viên đoàn được báo xe du lịch bị giữ ở cửa khẩu", "hướng dẫn viên trưởng đoàn", "Đoàn phải nộp phí bảo lãnh để tiếp tục hành trình", "tài khoản giả nhắn riêng thay vì thông báo qua công ty", "góp tiền bảo lãnh xe vào ví cá nhân", "mất tiền trong lúc đang ở xa nhà", "Cả đoàn sẽ lỡ lịch nếu không đủ tiền ngay"),
    ScenarioRoot("airline-baggage-compensation", "Hành khách được báo hành lý thất lạc đã được tìm thấy", "nhân viên bộ phận hành lý hãng bay", "Hãng cần xác minh tài khoản để trả bồi thường", "biểu mẫu giả yêu cầu số thẻ và mã bảo mật", "điền thông tin thẻ vào biểu mẫu nhận bồi thường", "thẻ bị sử dụng cho giao dịch trái phép", "Yêu cầu bồi thường sẽ tự đóng trong hôm nay"),
    ScenarioRoot("visa-appointment-hold", "Người xin thị thực được báo có lịch hẹn sớm", "nhân viên trung tâm tiếp nhận thị thực", "Lịch trống cần phí giữ chỗ", "thư hẹn giả dùng mã hồ sơ đúng lấy từ nhóm tư vấn", "chuyển phí giữ lịch phỏng vấn vào tài khoản trung gian", "mất phí và có thể lộ hồ sơ hộ chiếu", "Lịch hẹn sẽ chuyển cho ứng viên kế tiếp"),
    ScenarioRoot("lecturer-exam-file", "Sinh viên được báo đề cương thi vừa thay đổi", "giảng viên bộ môn", "Tài liệu mới nằm trong tệp bảo mật", "tệp thực thi được ngụy trang thành tài liệu học tập", "cài chương trình để mở đề cương thi", "máy tính nhiễm mã độc và mất tài khoản học tập", "Phải đọc trước tiết ôn tập sáng mai"),
    ScenarioRoot("thesis-plagiarism-login", "Sinh viên được báo luận văn có tỷ lệ trùng lặp cao", "giảng viên hướng dẫn", "Bản báo cáo chi tiết cần đăng nhập cổng kiểm tra", "trang giả sao chép giao diện hệ thống trường", "đăng nhập email trường để xem báo cáo đạo văn", "mất tài khoản email và dữ liệu luận văn", "Hạn sửa luận văn kết thúc tối nay"),
    ScenarioRoot("student-union-event-fee", "Thành viên câu lạc bộ được báo đã được chọn đi sự kiện", "ban chủ nhiệm câu lạc bộ", "Ban tổ chức cần thu phí đồng phục và xe", "một nhóm Zalo mới được tạo ngoài nhóm chính thức", "đóng phí sự kiện vào tài khoản thủ quỹ mới", "mất tiền và lộ danh sách sinh viên", "Chỉ giữ suất cho người nộp trước"),
    ScenarioRoot("course-certificate-unlock", "Học viên được báo đã đủ điều kiện nhận chứng chỉ", "trợ giảng khóa học trực tuyến", "Chứng chỉ số đang bị khóa vì thiếu phí xác thực", "ảnh bảng điểm thật được ghép với cổng thanh toán giả", "nộp phí mở khóa chứng chỉ qua đường dẫn", "mất phí và mật khẩu học tập", "Liên kết chứng chỉ hết hạn sau một giờ"),
    ScenarioRoot("gaming-item-escrow", "Người chơi được mời mua vật phẩm hiếm", "quản trị viên bang hội", "Vật phẩm phải qua tài khoản trung gian để tránh lừa đảo", "tài khoản giả dùng lịch sử trò chuyện của quản trị viên thật", "chuyển vật phẩm và tiền cho tài khoản ký quỹ", "mất cả vật phẩm lẫn tiền", "Giao dịch phải xong trước giờ mở máy chủ"),
    ScenarioRoot("livestream-giveaway-tax", "Người theo dõi được báo trúng quà từ buổi phát trực tiếp", "quản lý của người sáng tạo nội dung", "Giải thưởng cần nộp thuế và phí vận chuyển", "video cắt ghép có tên người nhận được gửi riêng", "chuyển phí nhận thưởng vào tài khoản trợ lý", "mất nhiều khoản phí cho giải thưởng giả", "Giải sẽ bị quay lại nếu không xác nhận ngay"),
    ScenarioRoot("romance-overseas-emergency", "Người đang hẹn hò qua mạng nhận tin đối phương gặp nạn", "người yêu đang làm việc ở nước ngoài", "Đối phương bị giữ hộ chiếu và cần tiền luật sư", "mối quan hệ được vun đắp nhiều tuần trước khi hỏi tiền", "chuyển tiền cứu trợ qua dịch vụ chuyển tiền quốc tế", "mất tiền vì quan hệ tình cảm giả", "Không thể gọi video vì đang ở khu vực an ninh"),
    ScenarioRoot("military-secure-call", "Bạn cũ nói đang làm nhiệm vụ tại đơn vị quân đội", "người bạn đang phục vụ trong quân đội", "Đơn vị chỉ cho phép liên lạc qua ứng dụng bảo mật", "hình quân phục được dùng để thuyết phục cài phần mềm lạ", "cài ứng dụng liên lạc ngoài kho chính thức", "điện thoại bị cài mã độc theo dõi", "Tài khoản liên lạc sẽ đóng sau ca trực"),
    ScenarioRoot("customs-overseas-parcel", "Người nhận được báo có quà từ họ hàng ở nước ngoài", "nhân viên hải quan cửa khẩu", "Bưu kiện chứa hàng giá trị và đang thiếu thuế", "ảnh kiện hàng gắn tên người nhận được tạo giả", "nộp thuế thông quan vào tài khoản cá nhân", "mất tiền qua nhiều lần phí phát sinh", "Bưu kiện sẽ bị tiêu hủy trong ngày"),
    ScenarioRoot("lottery-prize-tax", "Người dùng được báo số điện thoại trúng chương trình quay thưởng", "thư ký hội đồng trao giải", "Giải tiền mặt cần hoàn tất nghĩa vụ thuế", "giấy chứng nhận có con dấu giả được gửi qua Zalo", "chuyển thuế giải thưởng trước khi nhận tiền", "mất tiền cho giải thưởng không tồn tại", "Kết quả sẽ bị hủy nếu tiết lộ cho người khác"),
    ScenarioRoot("crypto-wallet-validation", "Thành viên nhóm đầu tư được báo ví tiền số có lỗi", "chuyên gia quản trị cộng đồng tiền số", "Ví phải đồng bộ để nhận đợt phân phối token", "trang hỗ trợ giả yêu cầu cụm từ khôi phục", "nhập mười hai từ khôi phục ví vào biểu mẫu", "toàn bộ tài sản số bị chuyển đi", "Đợt phân phối kết thúc sau ba mươi phút"),
    ScenarioRoot("investment-insider-deposit", "Nhà đầu tư được mời vào nhóm giao dịch nội bộ", "trợ lý của chuyên gia chứng khoán", "Một mã cổ phiếu sắp có tin chưa công bố", "ảnh lợi nhuận của thành viên giả tạo hiệu ứng đám đông", "chuyển tiền đặt cọc để nhận tín hiệu mua", "mất tiền trong mô hình đầu tư giả", "Cơ hội chỉ dành cho mười người đầu tiên"),
    ScenarioRoot("debt-settlement-threat", "Người nhận bị báo đang có khoản nợ của người thân", "nhân viên pháp chế công ty thu hồi nợ", "Hồ sơ sắp được chuyển sang khởi kiện", "kẻ gửi đe dọa đăng ảnh và gọi cho danh bạ", "chuyển khoản dàn xếp vào tài khoản nhân viên", "mất tiền do bị cưỡng ép bằng thông tin giả", "Lệnh khởi kiện sẽ phát hành trong một giờ"),
    ScenarioRoot("loan-disbursement-insurance", "Người vay được báo khoản vay đã được duyệt", "nhân viên giải ngân công ty tài chính", "Khoản vay cần mua bảo hiểm tín dụng bắt buộc", "hợp đồng giả hiển thị số tiền vay lớn", "đóng phí bảo hiểm trước khi giải ngân", "mất phí và tiếp tục bị yêu cầu nộp thêm", "Hồ sơ vay sẽ hủy cuối ngày"),
    ScenarioRoot("property-reservation-deposit", "Người mua nhà được mời giữ căn hộ giá tốt", "môi giới của chủ đầu tư", "Căn hộ vừa có khách khác hỏi mua", "bảng giá và phiếu giữ chỗ giả được gửi trong nhóm Zalo", "đặt cọc giữ căn vào tài khoản của môi giới", "mất khoản cọc cho dự án hoặc môi giới giả", "Chủ đầu tư chỉ giữ giá trong hai mươi phút"),
    ScenarioRoot("vehicle-inspection-deposit", "Người mua xe cũ được báo có thể xem xe từ xa", "nhân viên salon ô tô", "Xe đang ở kho khác và cần phí điều chuyển", "video xe bị sao chép từ một tin rao cũ", "đặt cọc phí đưa xe về điểm kiểm tra", "mất tiền cọc cho chiếc xe không tồn tại", "Xe sẽ bán cho khách tại kho nếu chưa cọc"),
    ScenarioRoot("lawyer-inheritance-release", "Người nhận được báo có tên trong hồ sơ thừa kế", "luật sư đại diện cho họ hàng xa", "Tài sản cần phí công chứng để được giải ngân", "văn bản pháp lý giả dùng thông tin gia đình thu thập trên mạng", "nộp phí công chứng hồ sơ thừa kế", "mất phí và lộ giấy tờ gia đình", "Hồ sơ sẽ chuyển vào tài sản vô chủ nếu chậm"),
    ScenarioRoot("appliance-warranty-recall", "Chủ nhà được báo máy điều hòa thuộc lô phải thu hồi", "kỹ thuật viên trung tâm bảo hành", "Thiết bị cần được đổi bo mạch miễn phí", "người gửi biết số máy từ ảnh hóa đơn bảo hành công khai", "đặt cọc lịch sửa chữa và cung cấp mã cửa căn hộ", "mất tiền cọc và tạo nguy cơ xâm nhập nhà", "Đội kỹ thuật chỉ còn một lịch trống hôm nay"),
    ScenarioRoot("lost-found-identity-check", "Người dùng được báo có ví giấy tờ được nhặt thấy", "quản trị viên nhóm đồ thất lạc", "Người nhận phải chứng minh mình là chủ sở hữu", "kẻ gửi mô tả đúng vài chi tiết công khai rồi xin thêm giấy tờ", "gửi ảnh căn cước và ảnh selfie cầm giấy tờ", "danh tính bị dùng để mở tài khoản giả", "Đồ sẽ được giao cho người nhận khác nếu không xác minh"),
)


def raw_variants_for_root(root: ScenarioRoot) -> list[dict[str, Any]]:
    """Return five explicitly authored direct messages for one semantic root."""
    try:
        templates = DIRECT_MESSAGE_TEMPLATES[root.anchor]
    except KeyError as exc:
        raise ValueError(f"no direct-message templates for root {root.anchor!r}") from exc

    try:
        direct_action = DIRECT_ACTIONS[root.anchor]
    except KeyError as exc:
        raise ValueError(f"no sender-natural direct action for root {root.anchor!r}") from exc

    texts = tuple(
        template.format(requested_action=direct_action) for template in templates
    )
    explanation = (
        f"Tin nhắn tạo áp lực xử lý gấp và yêu cầu {direct_action}, "
        f"có thể dẫn đến {root.consequence}."
    )
    return [
        {
            "text": text,
            "label": "zalo_social_engineering",
            "risk_tier": "high-risk",
            "suspicious_spans": [direct_action],
            "xai_explanation": explanation,
        }
        for text in texts
    ]
