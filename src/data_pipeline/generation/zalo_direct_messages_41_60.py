"""Direct sender-message templates for Zalo scenario roots 41 through 60.

These strings are locally authored dataset content, not prompts for a provider.
Each template contains one ``{requested_action}`` slot; materialization replaces
it with the sender-natural direct action so the evidence span remains exact.
The placeholder name is retained only as a stable formatting contract; legacy
``ScenarioRoot.requested_action`` wording is not inserted here.
"""

from __future__ import annotations


DIRECT_MESSAGE_TEMPLATES_41_60: dict[str, tuple[str, str, str, str, str]] = {
    "visa-appointment-hold": (
        "Trung tâm vừa mở thêm một lịch phỏng vấn sớm cho hồ sơ của anh/chị. Để khóa lịch trong hôm nay, vui lòng {requested_action}; quá giờ chúng tôi sẽ chuyển suất cho hồ sơ kế tiếp.",
        "Hồ sơ thị thực của anh/chị có thể chuyển sang ca hẹn tuần này. Anh/chị cần {requested_action} ngay để hệ thống giữ chỗ, nếu chậm lịch sẽ tự động trả về danh sách chờ.",
        "Tôi đang phụ trách lịch hẹn tại trung tâm tiếp nhận thị thực. Hiện còn một suất trống và anh/chị phải {requested_action} trước khi tôi xác nhận mã lịch.",
        "Anh/chị phản hồi gấp giúp tôi: ca phỏng vấn sớm chỉ được giữ khi đã {requested_action}. Sau thời hạn này hệ thống sẽ mời ứng viên khác.",
        "Bộ phận lịch hẹn đã ưu tiên hồ sơ của anh/chị vào khung giờ mới. Vui lòng {requested_action} để hoàn tất giữ suất, lịch chưa thanh toán sẽ bị hủy cuối buổi.",
    ),
    "lecturer-exam-file": (
        "Thầy vừa cập nhật đề cương thi cho lớp, bản mới chỉ mở bằng chương trình bảo mật này. Em hãy {requested_action} trước buổi ôn sáng mai; em nhớ kiểm tra đủ nội dung.",
        "Đề cương cũ không còn dùng cho kỳ thi tới. Các em cần {requested_action} ngay tối nay, mở xong nhớ đọc phần câu hỏi bổ sung trước tiết ôn.",
        "Tôi gửi lại tài liệu ôn tập đã khóa theo lớp. Em vui lòng {requested_action}; nếu để đến sáng mai hệ thống sẽ đóng quyền truy cập.",
        "Lớp mình có thay đổi cấu trúc đề thi và tệp mới không mở bằng trình đọc thông thường. Em phải {requested_action} ngay tối nay; phần hướng dẫn chấm điểm nằm trong bản mới.",
        "Nhà trường yêu cầu đọc bản đề cương bảo mật trước giờ ôn tập. Em làm ngay bước {requested_action}, rồi báo tôi khi màn hình hiện đủ các chương.",
    ),
    "thesis-plagiarism-login": (
        "Bản kiểm tra luận văn của em đang báo tỷ lệ trùng lặp cao và cần sửa trước tối nay. Em hãy {requested_action} rồi kiểm tra chi tiết từng đoạn.",
        "Thầy đã nhận kết quả đối chiếu luận văn nhưng cổng chỉ hiển thị khi xác thực sinh viên. Em cần {requested_action}, kiểm tra các phần tô màu rồi gửi lại bản sửa.",
        "Hạn chỉnh luận văn kết thúc tối nay, trong khi báo cáo đạo văn còn nhiều mục cần xử lý. Em vui lòng {requested_action} ngay và tải bảng kết quả.",
        "Cổng kiểm tra vừa khóa bản báo cáo của em do chưa xác nhận tài khoản trường. Em {requested_action} ngay hôm nay; thầy cần em xử lý các phần trùng lặp trước hạn.",
        "Luận văn chưa thể chuyển sang vòng duyệt vì hệ thống cần đối chiếu danh tính sinh viên. Em phải {requested_action}, sau đó mở mục Similarity Report và sửa ngay.",
    ),
    "student-union-event-fee": (
        "Câu lạc bộ đã chọn bạn tham gia sự kiện cuối tuần và đang chốt xe cùng đồng phục. Bạn hãy {requested_action} hôm nay để giữ suất.",
        "Danh sách đoàn chỉ còn thiếu xác nhận của bạn. Muốn nhận áo và có chỗ trên xe, bạn cần {requested_action}; ban tổ chức ưu tiên người hoàn tất trước.",
        "Mình đang tổng hợp phí cho chuyến sự kiện của câu lạc bộ. Bạn vui lòng {requested_action} rồi gửi ảnh giao dịch để mình đánh dấu đã giữ chỗ.",
        "Suất tham dự của bạn chỉ được giữ đến cuối buổi vì có người đang chờ thay. Làm giúp ban tổ chức bước {requested_action} để khóa tên trong danh sách.",
        "Bạn đã qua vòng chọn thành viên đi sự kiện. Bây giờ cần {requested_action} để xác nhận phần xe và đồng phục, quá hạn hệ thống sẽ nhường suất.",
    ),
    "course-certificate-unlock": (
        "Bạn đã hoàn thành đủ bài học nhưng chứng chỉ số đang chờ xác thực. Vui lòng {requested_action} trong một giờ tới để nhận liên kết tải chứng chỉ.",
        "Hệ thống ghi nhận khóa học của bạn đã đạt yêu cầu. Bạn cần {requested_action} trước khi liên kết hết hiệu lực.",
        "Tôi phụ trách cấp chứng chỉ cho lớp này và hồ sơ của bạn còn thiếu bước xác nhận cuối. Hãy {requested_action}, sau đó chứng chỉ sẽ gửi về email ngay.",
        "Chứng chỉ của bạn đã tạo xong nhưng chưa thể phát hành vì phí xác thực còn treo. Bạn làm ngay bước {requested_action} để tránh phải đăng ký cấp lại.",
        "Cổng học tập chỉ giữ bản chứng chỉ này thêm sáu mươi phút. Muốn tải bản có mã kiểm tra, bạn phải {requested_action} trước khi phiên đóng.",
    ),
    "gaming-item-escrow": (
        "Món đồ hiếm đã được khóa theo thỏa thuận đổi vật phẩm bù tiền của mình. Bạn hãy {requested_action} trước giờ mở máy chủ để mình bàn giao món mới.",
        "Tôi đã đưa món đồ hiếm vào kho trung gian và đang chờ phần trao đổi từ phía bạn. Bạn {requested_action} ngay; xong tôi sẽ duyệt lệnh nhận đồ.",
        "Có người khác đang hỏi món này nên mình chỉ giữ đến lúc máy chủ mở. Bạn {requested_action} để chốt thỏa thuận đổi vật phẩm bù tiền.",
        "Bang hội yêu cầu cả tiền lẫn vật phẩm được ký quỹ trước khi đổi chủ. Bạn vui lòng {requested_action}; hoàn tất rồi gửi mã giao dịch cho tôi.",
        "Phiên đổi vật phẩm bù tiền sắp hết thời gian bảo lưu. Muốn nhận món đồ đã thỏa thuận, bạn phải {requested_action} ngay trong ca này.",
    ),
    "livestream-giveaway-tax": (
        "Bạn đã trúng phần quà trong buổi phát trực tiếp tối nay. Để nhận giải theo địa chỉ đăng ký, bạn vui lòng {requested_action} ngay trước khi hệ thống chuyển suất cho người dự phòng.",
        "Tên của bạn đang ở vị trí nhận thưởng nhưng hồ sơ còn thiếu thuế và vận chuyển. Bạn cần {requested_action}, rồi tôi sẽ cấp mã giao quà.",
        "Mình phụ trách giải thưởng của kênh và phần quà của bạn đã được đóng gói. Bạn hãy {requested_action} để bên vận chuyển nhận đơn trong hôm nay.",
        "Giải của bạn chỉ được giữ trong phiên xác nhận này. Muốn hoàn tất thủ tục nhận quà, bạn phải {requested_action} trước khi danh sách chuyển sang người dự phòng.",
        "Hệ thống đã chọn đúng tài khoản của bạn từ buổi livestream. Vui lòng {requested_action} và gửi biên nhận để chúng tôi kích hoạt lệnh giao thưởng.",
    ),
    "romance-overseas-emergency": (
        "Anh đang bị giữ hộ chiếu ở đây và luật sư yêu cầu thanh toán ngay mới làm hồ sơ. Em giúp anh {requested_action}; khu vực này không cho gọi video.",
        "Em ơi, anh gặp sự cố ở nước ngoài và chưa thể rời khỏi chỗ kiểm tra. Anh cần em {requested_action} để luật sư đến bảo lãnh, đừng chờ đến ngày mai.",
        "Điện thoại của anh chỉ nhắn được vài phút nên em đừng gọi lại. Làm ơn {requested_action} ngay, có khoản này luật sư mới lấy hộ chiếu cho anh.",
        "Anh đang rất cần em giúp vì giấy tờ bị giữ và họ sắp đóng văn phòng. Em hãy {requested_action}; khi ra ngoài anh sẽ gọi giải thích đầy đủ.",
        "Tình hình ở đây khẩn lắm, anh không được phép bật camera trong khu an ninh. Em vui lòng {requested_action} để hoàn tất phí luật sư trước giờ đóng cửa.",
    ),
    "military-secure-call": (
        "Tớ đang trực trong đơn vị nên không dùng ứng dụng gọi thông thường được. Cậu hãy {requested_action} để mình nói chuyện trước khi tài khoản ca trực đóng.",
        "Đơn vị chỉ mở kênh liên lạc bảo mật trong ít phút. Bạn cần {requested_action}, vào bằng mã mình gửi rồi gọi lại ngay.",
        "Mình đang làm nhiệm vụ nên camera và cuộc gọi Zalo đều bị chặn. Cậu vui lòng {requested_action} để kết nối qua kênh nội bộ trước khi hết ca.",
        "Lâu rồi mới liên lạc được với cậu, nhưng ở đây chỉ cho dùng phần mềm riêng. Làm giúp mình bước {requested_action}; tài khoản này sẽ đóng sau ca trực.",
        "Tớ không thể gọi từ số cũ khi đang ở đơn vị. Muốn nói chuyện ngay bây giờ, cậu phải {requested_action} rồi nhập mã truy cập mình gửi sau.",
    ),
    "customs-overseas-parcel": (
        "Bưu kiện quà từ nước ngoài của anh/chị đang bị giữ vì thiếu thuế nhập khẩu. Anh/chị cần {requested_action} hôm nay để chúng tôi cho thông quan.",
        "Hải quan đã kiểm tra kiện hàng có giá trị gửi về tên anh/chị. Vui lòng {requested_action}; quá giờ xử lý kiện sẽ chuyển sang diện tiêu hủy.",
        "Tôi đang phụ trách hồ sơ thông quan của kiện quà này. Anh/chị hãy {requested_action} ngay, có biên nhận tôi mới cấp lệnh giao cho bưu cục.",
        "Mã kiện hàng của anh/chị còn một khoản thuế chưa hoàn tất. Để tránh bị trả hoặc hủy trong ngày, anh/chị phải {requested_action} trước giờ chốt.",
        "Kiện quà đang ở cửa khẩu và chỉ được lưu đến cuối ngày. Anh/chị vui lòng {requested_action}, rồi gửi ảnh giao dịch để tôi mở tờ khai.",
    ),
    "lottery-prize-tax": (
        "Số điện thoại của anh/chị vừa trúng giải tiền mặt trong chương trình quay thưởng. Anh/chị cần {requested_action} và giữ kín kết quả đến khi giải ngân.",
        "Hội đồng đã xác nhận anh/chị là chủ nhân của giải hôm nay. Vui lòng {requested_action}; sau đó chúng tôi sẽ chuyển toàn bộ tiền thưởng.",
        "Tôi phụ trách thủ tục trao giải và hồ sơ của anh/chị chỉ còn nghĩa vụ thuế. Anh/chị hãy {requested_action} ngay để không bị hủy kết quả.",
        "Giải tiền mặt đang chờ phát hành về tài khoản của anh/chị. Muốn kích hoạt lệnh chuyển, anh/chị phải {requested_action} trong thời hạn ghi trên hệ thống.",
        "Chúc mừng anh/chị đã có tên trong danh sách trúng thưởng. Hãy {requested_action}, không chia sẻ thông tin này với ai cho đến khi nhận mã giải.",
    ),
    "crypto-wallet-validation": (
        "Ví của bạn đang lỗi đồng bộ nên chưa nhận được đợt phân phối token. Bạn cần {requested_action} trong ba mươi phút để khôi phục quyền nhận.",
        "Hệ thống cộng đồng không xác nhận được ví hiện tại của bạn. Hãy {requested_action}, sau đó công cụ sẽ đồng bộ số dư và mở phần token mới.",
        "Tôi đang hỗ trợ danh sách airdrop và địa chỉ ví của bạn báo thiếu bước xác minh. Bạn vui lòng {requested_action} trước khi đợt phân phối kết thúc.",
        "Suất token của ví này chỉ được giữ đến cuối phiên. Muốn liên kết lại ví và nhận phân bổ, bạn phải {requested_action} ngay bây giờ.",
        "Cổng quản trị vừa đánh dấu ví của bạn cần khôi phục trước khi nhận token. Làm ngay bước {requested_action}; chậm hơn hệ thống sẽ bỏ qua địa chỉ này.",
    ),
    "investment-insider-deposit": (
        "Nhóm nội bộ sắp vào lệnh một mã có tin lớn chưa công bố. Muốn nhận điểm mua trước thị trường, anh/chị cần {requested_action}; chỉ mười suất đầu được duyệt.",
        "Chuyên gia đang chốt danh sách cho tín hiệu giao dịch đặc biệt tối nay. Anh/chị hãy {requested_action} ngay; sau đó hệ thống sẽ mở mã cổ phiếu và mức giá vào lệnh.",
        "Tôi là trợ lý quản lý nhóm đầu tư kín. Nhóm chỉ nhận mười người đầu tiên; anh/chị hoàn tất bước {requested_action} trước khi danh sách đủ thành viên.",
        "Một mã cổ phiếu chuẩn bị có biến động mạnh và nhóm sẽ công bố điểm mua trong ít phút. Anh/chị phải {requested_action} ngay hôm nay; hoàn tất xong tôi sẽ thêm anh/chị vào phòng tín hiệu.",
        "Danh sách giao dịch nội bộ còn đúng một vị trí. Nếu muốn nhận khuyến nghị mua sớm, anh/chị vui lòng {requested_action} trước khi chúng tôi khóa nhóm.",
    ),
    "debt-settlement-threat": (
        "Hồ sơ nợ đứng tên người thân của anh/chị sắp chuyển sang khởi kiện. Để dừng thủ tục trong hôm nay, anh/chị phải {requested_action} ngay.",
        "Bộ phận pháp chế chỉ cho một giờ để xử lý khoản nợ này trước khi phát hành đơn kiện. Anh/chị cần {requested_action} và gửi biên nhận cho tôi.",
        "Tôi đang phụ trách hồ sơ thu hồi nợ liên quan đến gia đình anh/chị. Muốn chốt phương án dàn xếp, vui lòng {requested_action} trước giờ lập lệnh.",
        "Nếu anh/chị không xử lý ngay, hồ sơ sẽ được chuyển sang thủ tục pháp lý. Cách duy nhất để tạm dừng là {requested_action} trong phiên làm việc này.",
        "Khoản nợ đã đến bước chuẩn bị khởi kiện và tôi không thể gia hạn thêm. Anh/chị hãy {requested_action} để chúng tôi ghi nhận dàn xếp khẩn.",
    ),
    "loan-disbursement-insurance": (
        "Khoản vay của anh/chị đã được duyệt và đang chờ lệnh chuyển tiền. Anh/chị cần {requested_action} hôm nay để kích hoạt lệnh chi.",
        "Hồ sơ tín dụng đã qua thẩm định nhưng còn thiếu bảo hiểm bắt buộc. Vui lòng {requested_action}, sau đó tiền vay sẽ chuyển về tài khoản đăng ký.",
        "Tôi đang xử lý bước cuối cho hợp đồng vay của anh/chị. Hãy {requested_action} trong hôm nay; quá giờ hệ thống sẽ hủy hồ sơ.",
        "Hạn mức vay đã khóa theo thông tin anh/chị cung cấp. Muốn nhận tiền trong ca này, anh/chị phải {requested_action}; hệ thống sẽ đóng hồ sơ cuối ca.",
        "Công ty tài chính đã sẵn sàng giải ngân khoản vay. Anh/chị vui lòng {requested_action} và gửi xác nhận để tôi phát hành lệnh chuyển.",
    ),
    "property-reservation-deposit": (
        "Căn hộ anh/chị vừa xem đang có khách khác hỏi mua và chủ đầu tư chỉ giữ giá thêm hai mươi phút. Anh/chị cần {requested_action} để khóa căn.",
        "Tôi đã xin giữ căn đúng tầng cho anh/chị nhưng bộ phận bán hàng cần xác nhận ngay. Vui lòng {requested_action}, sau đó tôi gửi phiếu giữ chỗ.",
        "Bảng giá ưu đãi của căn này sắp hết hiệu lực. Nếu anh/chị muốn giữ đúng mức giá đã trao đổi, hãy {requested_action} trước khi hệ thống nhả căn.",
        "Chủ đầu tư yêu cầu có giao dịch xác nhận mới bảo lưu căn hộ. Anh/chị phải {requested_action} trong phiên này vì một khách khác đang chờ.",
        "Căn cuối cùng của đợt mở bán vẫn còn tên anh/chị trong danh sách tạm giữ. Làm ngay bước {requested_action} để tôi chốt mã căn và giá.",
    ),
    "vehicle-inspection-deposit": (
        "Chiếc xe anh/chị hỏi đang ở kho khác và salon cần phí điều chuyển về điểm xem. Anh/chị hãy {requested_action} hôm nay để giữ xe.",
        "Tôi đã kiểm tra xe còn hàng nhưng kho chỉ chuyển đi khi có xác nhận. Vui lòng {requested_action}, xe sẽ được đưa về để anh/chị kiểm tra trực tiếp.",
        "Có khách tại kho đang muốn lấy chiếc xe này. Nếu anh/chị cần salon chuyển xe về xem trước, phải {requested_action} ngay để khóa đơn.",
        "Salon có thể sắp xếp xem xe từ xa rồi đưa xe về điểm hẹn. Anh/chị cần {requested_action}, hoàn tất tôi sẽ gửi lịch điều chuyển.",
        "Phiếu điều xe chỉ còn hiệu lực trong hôm nay. Anh/chị vui lòng {requested_action} trước giờ đóng kho để chúng tôi không bán xe cho khách khác.",
    ),
    "lawyer-inheritance-release": (
        "Tôi đang xử lý hồ sơ thừa kế có ghi tên anh/chị trong danh sách hưởng tài sản. Anh/chị cần {requested_action}; có biên nhận tôi sẽ mở lệnh giải ngân.",
        "Phần tài sản từ người họ hàng xa đang chờ xác nhận pháp lý. Vui lòng {requested_action} sớm, nếu quá hạn hồ sơ sẽ chuyển sang diện vô chủ.",
        "Văn phòng đã hoàn tất đối chiếu thông tin gia đình của anh/chị. Bước còn lại là {requested_action}; có xác nhận tôi mới phát hành giấy nhận thừa kế.",
        "Hồ sơ phân chia tài sản chỉ được bảo lưu đến cuối kỳ xử lý này. Anh/chị phải {requested_action} ngay để giữ quyền nhận phần thừa kế.",
        "Tôi là luật sư đại diện cho nhánh gia đình đang làm thủ tục di sản. Anh/chị hãy {requested_action}, rồi tôi sẽ gửi lịch ký và chứng từ giải ngân.",
    ),
    "appliance-warranty-recall": (
        "Máy điều hòa nhà anh/chị thuộc lô cần thay bo mạch và trung tâm chỉ còn một lịch kỹ thuật hôm nay. Vui lòng {requested_action} để khóa lịch.",
        "Bộ phận bảo hành đã duyệt thay linh kiện miễn phí cho máy của anh/chị. Anh/chị cần {requested_action}, sau đó tôi sắp xếp kỹ thuật viên đến.",
        "Số máy trên phiếu bảo hành nằm trong đợt thu hồi khẩn. Để nhận lịch sửa trong hôm nay, anh/chị hãy {requested_action} trước giờ điều phối.",
        "Tôi đang xếp lịch đổi bo mạch cho thiết bị của anh/chị. Suất cuối chỉ được giữ khi anh/chị {requested_action}; sau đó hãy xác nhận thời gian có mặt.",
        "Trung tâm cần hoàn tất thông tin vào cửa trước khi cử đội bảo hành. Anh/chị phải {requested_action}; chậm hơn lịch sẽ chuyển sang khách khác.",
    ),
    "lost-found-identity-check": (
        "Tôi đang giữ một chiếc ví có thông tin trùng với tên bạn. Để xác nhận đúng chủ trước khi giao, bạn cần {requested_action} ngay hôm nay.",
        "Nhóm đồ thất lạc vừa nhận một ví giấy tờ giống mô tả của bạn. Bạn hãy {requested_action} để tôi đối chiếu, nếu không món đồ sẽ được giao cho người xác minh trước.",
        "Mình phụ trách bàn giao chiếc ví vừa tìm thấy. Muốn nhận lại, bạn phải {requested_action}; có đủ thông tin mình mới sắp xếp điểm giao.",
        "Chiếc ví đang có thêm một người liên hệ nhận là của họ. Bạn vui lòng {requested_action} sớm để chứng minh quyền sở hữu trước khi chúng tôi bàn giao.",
        "Tôi đã đối chiếu vài chi tiết và có thể đây là giấy tờ của bạn. Làm giúp bước {requested_action}, hoàn tất tôi sẽ giữ ví lại thay vì chuyển cho người khác.",
    ),
}
