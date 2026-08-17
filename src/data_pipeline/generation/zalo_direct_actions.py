"""Sender-natural evidence actions for the 60 reconstructed Zalo roots.

Legacy ``ScenarioRoot.requested_action`` values are frozen because they are
part of the exact formulas used to validate the contaminated input. Some of
those values contain analyst language (for example, "tài khoản lạ") and must
not appear in a sender-authored message. This catalog decouples new wording
and exact evidence spans from that legacy validation field.
"""

from __future__ import annotations


DIRECT_ACTIONS: dict[str, str] = {
    "family-hospital-deposit": "quét mã QR này để chuyển khoản viện phí",
    "friend-stolen-wallet-loan": "chuyển ít tiền vào tài khoản này",
    "sibling-roadside-rescue": "đặt cọc phí cứu hộ qua ví điện tử này",
    "classmate-wedding-gift": "gửi tiền mừng qua mã QR đã ghim",
    "funeral-committee-contribution": "chuyển tiền phúng viếng vào tài khoản ban tổ chức này",
    "teacher-fieldtrip-fee": "nộp phí chuyến đi qua mã QR này",
    "principal-scholarship-processing": "chuyển phí xử lý hồ sơ học bổng",
    "landlord-rent-account-change": "chuyển toàn bộ tiền thuê tháng này vào tài khoản kế toán mới",
    "apartment-fire-registration": "mở biểu mẫu này và tải ảnh căn cước cùng ảnh khuôn mặt",
    "ceo-supplier-transfer": "chuyển gấp tiền công ty vào tài khoản nhà cung cấp này",
    "hr-payroll-verification": "điền mật khẩu email và thông tin ngân hàng vào biểu mẫu này",
    "it-remote-support": "cài ứng dụng điều khiển màn hình rồi gửi mã kết nối",
    "coworker-zalo-login-qr": "quét mã QR đăng nhập Zalo này",
    "recruiter-background-check": "nộp phí thẩm tra hồ sơ tuyển dụng",
    "freelance-escrow-activation": "đóng phí kích hoạt để mở khóa tiền ký quỹ",
    "courier-address-correction": "thanh toán phí sửa địa chỉ qua liên kết tôi gửi",
    "delivery-refund-screen-share": "bật chia sẻ màn hình rồi đọc mã xác nhận hoàn tiền",
    "seller-escrow-release": "đăng nhập ngân hàng tại liên kết này để mở khóa tiền bán",
    "buyer-chargeback-otp": "gửi mã OTP cho tôi để đóng hồ sơ khiếu nại",
    "zalo-account-recovery": "nhập số điện thoại và mật khẩu vào trang khôi phục này",
    "zalo-verified-badge": "chuyển phí cấp dấu xác minh vào tài khoản em gửi",
    "zalo-community-strike": "đăng nhập tại liên kết này để gửi đơn kháng nghị",
    "group-admin-vote": "quét mã QR này để xác nhận phiếu bầu",
    "police-confidential-investigation": "chuyển tiền vào tài khoản tạm giữ để chứng minh nguồn tiền",
    "court-summons-apk": "cài tệp ứng dụng này để mở giấy triệu tập điện tử",
    "tax-refund-app": "cài ứng dụng hoàn thuế rồi cấp quyền trợ năng",
    "ward-relief-registration": "tải ảnh hai mặt căn cước và nộp phí đăng ký",
    "social-insurance-benefit": "mở ứng dụng ngân hàng trong lúc đang chia sẻ màn hình",
    "electricity-disconnection": "quét mã QR tôi gửi để thanh toán lại hóa đơn",
    "water-meter-replacement": "đặt cọc chi phí thay đồng hồ nước",
    "telecom-esim-migration": "đọc mã OTP đổi SIM",
    "doctor-imported-medicine": "chuyển tiền mua thuốc vào tài khoản nhà thuốc tôi gửi",
    "pharmacy-scarce-medicine": "thanh toán trước toàn bộ tiền thuốc",
    "insurance-claim-inspection": "nộp phí giám định để giải ngân bồi thường",
    "charity-beneficiary-transfer": "chuyển tiền cứu trợ vào tài khoản tiếp nhận tạm thời",
    "pet-adoption-transport": "thanh toán phí vận chuyển và tiền thuê lồng",
    "travel-ticket-reissue": "trả phí đổi vé tại cổng thanh toán tôi gửi",
    "hotel-relocation-deposit": "chuyển thêm tiền cọc để giữ phòng thay thế",
    "tour-group-emergency": "góp tiền bảo lãnh xe vào ví tôi gửi",
    "airline-baggage-compensation": "điền thông tin thẻ vào biểu mẫu nhận bồi thường",
    "visa-appointment-hold": "chuyển phí giữ lịch phỏng vấn vào tài khoản tiếp nhận hồ sơ",
    "lecturer-exam-file": "cài chương trình này để mở đề cương thi",
    "thesis-plagiarism-login": "đăng nhập email trường tại cổng này để xem báo cáo đạo văn",
    "student-union-event-fee": "đóng phí sự kiện vào tài khoản thủ quỹ mới",
    "course-certificate-unlock": "nộp phí mở khóa chứng chỉ tại liên kết này",
    "gaming-item-escrow": "chuyển vật phẩm và tiền vào tài khoản ký quỹ",
    "livestream-giveaway-tax": "chuyển phí nhận thưởng vào tài khoản trợ lý",
    "romance-overseas-emergency": "chuyển khoản qua dịch vụ chuyển tiền quốc tế",
    "military-secure-call": "cài ứng dụng liên lạc nội bộ qua đường dẫn vừa gửi",
    "customs-overseas-parcel": "nộp thuế thông quan vào tài khoản thu ngân tôi gửi",
    "lottery-prize-tax": "nộp tiền thuế giải thưởng",
    "crypto-wallet-validation": "nhập mười hai từ khôi phục ví vào biểu mẫu này",
    "investment-insider-deposit": "chuyển tiền đặt cọc để nhận tín hiệu mua",
    "debt-settlement-threat": "chuyển khoản dàn xếp vào tài khoản xử lý hồ sơ này",
    "loan-disbursement-insurance": "đóng phí bảo hiểm trước khi giải ngân",
    "property-reservation-deposit": "đặt cọc giữ căn vào tài khoản tôi vừa gửi",
    "vehicle-inspection-deposit": "đặt cọc phí đưa xe về điểm kiểm tra",
    "lawyer-inheritance-release": "nộp phí công chứng hồ sơ thừa kế",
    "appliance-warranty-recall": "đặt cọc lịch sửa chữa và gửi mã cửa căn hộ",
    "lost-found-identity-check": "gửi ảnh căn cước và ảnh selfie cầm giấy tờ",
}
