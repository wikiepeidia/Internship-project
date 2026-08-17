"""Direct-message templates for Zalo scenario roots 21 through 40.

Every tuple contains five independently worded messages spoken directly by
the impersonated sender.  The caller substitutes the root-specific suspicious
action into the sole ``{requested_action}`` field in each template.
"""

from __future__ import annotations


DIRECT_MESSAGE_TEMPLATES_21_40: dict[str, tuple[str, str, str, str, str]] = {
    "zalo-verified-badge": (
        "Chào anh/chị, Zalo Business đã xét duyệt cửa hàng đủ điều kiện nhận dấu xác minh và tăng độ tin cậy khi bán hàng. Hồ sơ ưu tiên chỉ mở hôm nay, anh/chị {requested_action} để bên em cấp dấu ngay.",
        "Shop mình vừa đạt tiêu chí nâng cấp lên tài khoản chính thức rồi ạ. Em đang giữ suất hỗ trợ đến cuối ngày; anh/chị {requested_action}, sau đó em kích hoạt dấu xác minh cho trang.",
        "Bộ phận doanh nghiệp mời anh/chị hoàn tất bước cuối để trang bán hàng hiện huy hiệu xác thực. Phí duy trì năm đầu được miễn; anh/chị chỉ cần {requested_action} trong hôm nay.",
        "Em phụ trách hồ sơ Zalo Business của cửa hàng mình. Chứng nhận đã duyệt nhưng còn lệ phí phát hành, anh/chị {requested_action} trước 17 giờ để không mất quyền ưu tiên.",
        "Trang của anh/chị nằm trong đợt nâng hạng dành cho nhà bán uy tín, có thêm hiển thị tìm kiếm sau khi nhận dấu. Suất này hết hiệu lực tối nay nên mình {requested_action} giúp em nhé.",
    ),
    "zalo-community-strike": (
        "Chào quản trị viên, nhóm của anh/chị đang có khiếu nại bản quyền chưa xử lý và sẽ bị gỡ sau sáu giờ. Anh/chị {requested_action} ngay; bộ phận tiêu chuẩn sẽ tiếp nhận đơn.",
        "Hệ thống cộng đồng vừa khóa chức năng đăng bài của nhóm do nội dung bị tố cáo. Muốn giữ nguyên thành viên và lịch sử trò chuyện, bạn {requested_action} trước thời hạn hiển thị trên thông báo.",
        "Tôi đang phụ trách hồ sơ vi phạm của nhóm mình. Bên khiếu nại yêu cầu xóa nhóm trong hôm nay; anh/chị {requested_action} ngay hôm nay. Hệ thống cần đơn này để xác nhận quyền quản trị.",
        "Nhóm có một bài đăng bị chủ sở hữu nội dung yêu cầu xử lý khẩn. Nếu bạn không phản hồi trong sáu giờ, hệ thống sẽ xóa toàn bộ nhóm; hãy {requested_action} ngay bây giờ.",
        "Bộ phận tiêu chuẩn cộng đồng cần anh/chị xác nhận kháng nghị cho nhóm trước khi lệnh đình chỉ có hiệu lực. Vui lòng {requested_action} ngay, quá giờ chúng tôi không thể khôi phục dữ liệu.",
    ),
    "group-admin-vote": (
        "Cả nhà đang bầu lại ban quản trị để tránh người ngoài chiếm nhóm. Anh/chị {requested_action} trong mười phút giúp tôi, phiếu phải gắn với tài khoản đang tham gia nhóm mới được tính.",
        "Bạn còn thiếu bước xác nhận trong cuộc bỏ phiếu quản trị viên của khu mình. Vui lòng {requested_action} ngay, hệ thống chốt kết quả lúc hết mười phút.",
        "Tôi mở vòng biểu quyết nhanh vì quyền quản trị nhóm sắp hết hạn. Anh/chị {requested_action} trong mười phút tới; hệ thống chỉ ghi nhận phiếu gắn với tài khoản chính chủ.",
        "Nhóm cư dân cần đủ số phiếu xác thực để giữ ban quản trị hiện tại. Bạn {requested_action} giúp nhé, mã chỉ dùng cho vòng bỏ phiếu đang diễn ra và sắp hết hiệu lực.",
        "Anh/chị được chọn tham gia xác nhận quản trị viên mới của nhóm. Hãy {requested_action} trong ít phút tới, nếu thiếu phiếu hệ thống sẽ tạm đóng nhóm để kiểm tra.",
    ),
    "police-confidential-investigation": (
        "Tôi là cán bộ đang xác minh dòng tiền liên quan đến hồ sơ rửa tiền có tên anh/chị. Đây là chuyên án bảo mật, không trao đổi với người thân; anh/chị phải {requested_action} và giữ liên lạc đến khi đối soát xong.",
        "Anh/chị đang được yêu cầu hợp tác kiểm tra tài sản vì một tài khoản liên quan vụ án đã giao dịch với mình. Để hoàn tất kiểm tra tài sản, hãy {requested_action}; tuyệt đối không ngắt cuộc gọi trong thời gian xác minh.",
        "Hồ sơ của anh/chị vừa được chuyển sang tổ điều tra tài chính và lệnh phong tỏa có thể ban hành hôm nay. Anh/chị {requested_action} ngay, đồng thời không báo cho bất kỳ ai vì vụ việc có yếu tố đồng phạm.",
        "Tôi đã gửi thẻ công tác và mã hồ sơ cho anh/chị kiểm tra. Muốn tránh tạm giữ toàn bộ số dư, anh/chị cần {requested_action} ngay và ở lại cuộc gọi cho đến khi nhận biên bản xác nhận.",
        "Một đường dây đang sử dụng thông tin của anh/chị để luân chuyển tiền, nên việc kiểm tra phải tiến hành kín. Anh/chị {requested_action} theo hướng dẫn, không gọi lại ngân hàng hay gia đình trước khi chúng tôi kết thúc nghiệp vụ.",
    ),
    "court-summons-apk": (
        "Tôi là thư ký phụ trách hồ sơ có giấy triệu tập gửi anh/chị nhưng chưa ký nhận. Để xem nội dung trước buổi làm việc, anh/chị {requested_action}; nếu vắng mặt, tòa sẽ xử lý theo thủ tục khẩn.",
        "Anh/chị có văn bản tố tụng điện tử cần xác nhận trong hôm nay. Hệ thống hồ sơ không mở trực tiếp trên Zalo; vui lòng {requested_action} rồi đọc nội dung và phản hồi đúng hạn.",
        "Tòa đã hai lần chuyển giấy mời nhưng chưa nhận được chữ ký của anh/chị. Tôi gửi bộ đọc hồ sơ dành cho điện thoại; anh/chị {requested_action} ngay, quá giờ hồ sơ sẽ ghi nhận không hợp tác.",
        "Mã vụ việc của anh/chị đã đến hạn đối chiếu và buổi làm việc được xếp lịch gấp. Xin {requested_action} ngay; nếu không, tòa sẽ tiếp tục thủ tục mà không chờ xác nhận.",
        "Bộ phận văn thư cần anh/chị nhận giấy triệu tập qua điện thoại trước khi kết thúc ca trực. Anh/chị {requested_action}, mở xong báo lại tôi ngay để cập nhật trạng thái đã nhận.",
    ),
    "tax-refund-app": (
        "Cơ quan thuế đang có khoản hoàn nộp thừa cho anh/chị nhưng tài khoản nhận tiền chưa liên kết. Anh/chị {requested_action} trong hôm nay để hệ thống đối soát và chuyển khoản hoàn.",
        "Hồ sơ thuế cá nhân của anh/chị vừa phát sinh tiền được hoàn. Tôi hỗ trợ xử lý từ xa, vui lòng {requested_action}; quyền này cần thiết để hoàn tất liên kết ngân hàng trước khi hồ sơ hết hạn.",
        "Anh/chị đủ điều kiện nhận lại phần thuế đã khấu trừ, tuy nhiên cổng điện tử đang thiếu bước xác nhận thiết bị. Hãy {requested_action} ngay, cuối ngày lệnh hoàn sẽ tự hủy.",
        "Tôi phụ trách đợt hoàn thuế hôm nay và thấy hồ sơ của anh/chị chưa có tài khoản thụ hưởng. Anh/chị {requested_action}, giữ máy trực tuyến để tôi hướng dẫn đối soát từng bước.",
        "Khoản hoàn của anh/chị đã được duyệt nhưng chỉ còn chờ kích hoạt liên kết ngân hàng. Vui lòng {requested_action} trước 17 giờ để tiền không bị trả về ngân sách.",
    ),
    "ward-relief-registration": (
        "Chào anh/chị, hộ gia đình mình có tên trong danh sách hỗ trợ của phường nhưng chưa xác thực cư trú. Trước buổi phát quà, anh/chị {requested_action} để cán bộ chốt hồ sơ.",
        "Tổ an sinh đang bổ sung suất trợ cấp cho khu phố và nhà mình thuộc diện được nhận. Danh sách khóa chiều nay, anh/chị {requested_action} ngay để không bị chuyển suất.",
        "Em phụ trách hồ sơ cứu trợ của phường, hiện thông tin cư trú nhà anh/chị còn thiếu. Mình {requested_action} giúp em trước khi đoàn bắt đầu phát quà nhé.",
        "Phường đã duyệt khoản hỗ trợ cho gia đình anh/chị, nhưng hệ thống yêu cầu hoàn thiện xác minh người nhận. Vui lòng {requested_action}; quá thời hạn hôm nay hồ sơ sẽ bị loại khỏi đợt này.",
        "Anh/chị xác nhận nhận trợ cấp đợt khẩn cấp giúp tôi. Để đối chiếu đúng chủ hộ và giữ suất trong danh sách, anh/chị cần {requested_action} trước giờ phát.",
    ),
    "social-insurance-benefit": (
        "Tôi kiểm tra thấy anh/chị còn một khoản bảo hiểm chưa nhận do ứng dụng định danh hết hiệu lực. Giữ nguyên cuộc gọi và {requested_action} để tôi kích hoạt lại hồ sơ, thoát giữa chừng hồ sơ sẽ bị trả về.",
        "Hồ sơ hưởng bảo hiểm của anh/chị đang treo ở bước liên kết thanh toán. Anh/chị bật chia sẻ như tôi hướng dẫn rồi {requested_action}; xin đừng tắt cuộc gọi trước khi trạng thái chuyển sang hoàn tất.",
        "Bên bảo hiểm cần xác nhận tài khoản nhận quyền lợi trước khi giải ngân khoản còn thiếu. Anh/chị {requested_action}. Nếu ngắt phiên, anh/chị sẽ phải nộp lại hồ sơ từ đầu.",
        "Anh/chị có tiền chế độ tồn từ kỳ trước nhưng thông tin định danh đang lệch. Tôi sẽ đối chiếu trực tuyến ngay bây giờ; vui lòng {requested_action} và ở lại màn hình cho tới khi có mã hoàn tất.",
        "Ứng dụng bảo hiểm của anh/chị phải kích hoạt lại hôm nay để nhận khoản quyền lợi chưa chi. Mình {requested_action} theo từng bước tôi đọc, đừng thoát cuộc gọi kẻo hệ thống hủy phiên.",
    ),
    "electricity-disconnection": (
        "Tôi là nhân viên điện lực khu vực, hóa đơn nhà anh/chị đang bị treo do lỗi đối soát dù đã đến hạn. Đội ngừng cấp điện đang trên đường, anh/chị {requested_action} ngay để tôi hủy lệnh.",
        "Mã khách hàng của anh/chị còn một kỳ tiền điện chưa ghi nhận trên hệ thống. Muốn giữ điện hôm nay, vui lòng {requested_action}; thanh toán xong gửi tôi xác nhận để báo đội kỹ thuật quay về.",
        "Nhà mình sắp bị ngắt công tơ vì giao dịch tháng này không khớp mã hợp đồng. Anh/chị {requested_action} trước khi nhân viên đến địa chỉ, chậm hơn tôi không can thiệp được.",
        "Bộ phận thu cước đang xử lý danh sách nợ cuối ngày và địa chỉ anh/chị có trong danh sách cắt điện. Xin {requested_action} ngay, tôi sẽ cập nhật đã thanh toán và dừng lệnh tại chỗ.",
        "Anh/chị kiểm tra giúp hóa đơn điện: hệ thống báo chưa thu được tiền nên đã điều đội xuống khu vực. Để tránh bị ngắt nguồn, anh/chị {requested_action} trong vài phút tới rồi báo mã giao dịch cho tôi.",
    ),
    "water-meter-replacement": (
        "Tôi là kỹ thuật cấp nước phụ trách tuyến nhà anh/chị. Đồng hồ hiện tại không đạt kiểm định và cần đổi trong hôm nay; anh/chị {requested_action} để tôi giữ lịch, nếu bỏ lịch nguồn nước sẽ tạm ngừng.",
        "Phiếu công tác thay đồng hồ nước của căn hộ đã được xếp vào ca chiều. Anh/chị {requested_action} trước 11 giờ để xác nhận lịch, quá giờ đội kỹ thuật sẽ chuyển sang địa chỉ khác.",
        "Thiết bị đo nước nhà mình vừa bị đánh dấu sai chuẩn nên công ty yêu cầu thay khẩn. Vui lòng {requested_action}; hoàn tất rồi tôi gửi thời gian kỹ thuật viên đến lắp.",
        "Anh/chị xem phiếu hẹn tôi vừa gửi nhé, đây là đợt thay đồng hồ bắt buộc của khu. Muốn tránh tạm khóa van ngày mai, anh/chị {requested_action} ngay hôm nay.",
        "Đội cấp nước chỉ còn một khung giờ để xử lý đồng hồ của căn hộ mình. Anh/chị {requested_action} giúp tôi giữ ca, nếu không hệ thống sẽ ghi nhận từ chối kiểm định và ngừng cấp nước.",
    ),
    "telecom-esim-migration": (
        "Tôi hỗ trợ thuê bao của anh/chị chuyển sang eSIM vì SIM hiện tại sắp ngừng bắt sóng. Khi mã xác thực gửi về, anh/chị {requested_action}; phải hoàn tất trong mười lăm phút để giữ số.",
        "Nhà mạng đang nâng cấp hệ thống và số của anh/chị cần đổi hồ sơ SIM ngay hôm nay. Vui lòng {requested_action} để tôi kích hoạt eSIM trước khi SIM cũ bị vô hiệu.",
        "Thuê bao này đang ở trạng thái chờ chuyển eSIM, nếu hết phiên sẽ mất dịch vụ hai chiều. Anh/chị {requested_action} ngay khi nhận được mã qua tin nhắn, tôi sẽ hoàn tất trên hệ thống.",
        "Em là nhân viên kỹ thuật nhà mạng đang xử lý lỗi mất sóng cho số của anh/chị. Mình {requested_action} trong vòng mười lăm phút nhé, chậm hơn mã hết hạn và SIM vật lý sẽ bị khóa.",
        "Hồ sơ chuyển đổi eSIM của anh/chị chỉ thiếu bước xác nhận chính chủ. Anh/chị {requested_action} giúp tôi ngay, hệ thống sắp kết thúc phiên và không thể giữ lại số cũ sau đó.",
    ),
    "doctor-imported-medicine": (
        "Tôi là bác sĩ đang theo dõi ca của người nhà anh/chị. Thuốc hiện dùng đã hết, tôi vừa giữ được một hộp nhập khẩu đến cuối giờ; gia đình {requested_action} để lấy thuốc kịp liệu trình.",
        "Tình trạng của bệnh nhân cần duy trì thuốc liên tục nhưng kho bệnh viện không còn loại này. Anh/chị {requested_action} ngay; nhà thuốc sẽ giữ lô hàng đến hết ca.",
        "Tôi đã gửi toa và hình hộp thuốc để gia đình đối chiếu. Lô nhập chỉ còn ít và bên bán cần chốt trước chiều nay, anh/chị {requested_action} để họ giao thẳng vào viện.",
        "Ca điều trị không nên hoãn thêm, trong khi nhà thuốc vừa báo có suất thuốc cuối cùng cho bệnh nhân. Gia đình vui lòng {requested_action}; quá cuối giờ họ sẽ chuyển cho người khác.",
        "Anh/chị thu xếp thuốc cho người nhà ngay giúp tôi. Tôi đã nhờ đầu mối giữ riêng một liều nhưng họ chỉ xác nhận khi gia đình {requested_action}, nếu chậm sẽ lỡ lịch dùng tối nay.",
    ),
    "pharmacy-scarce-medicine": (
        "Nhà thuốc đã kiểm tra toàn hệ thống và kho bên kia còn đúng một hộp loại anh/chị hỏi. Có khách khác đang chờ, anh/chị {requested_action} để em khóa đơn và chuyển thuốc về.",
        "Thuốc cho người nhà anh/chị hiện chỉ còn ở chi nhánh xa, em có thể giữ đến hết mười phút. Mình {requested_action} ngay để kho ngừng bán hộp đó cho khách khác.",
        "Em vừa nhận phản hồi rằng lô thuốc hiếm còn một suất giao hôm nay. Anh/chị {requested_action}, bên em xác nhận xong sẽ cho xe chuyển thẳng đến địa chỉ.",
        "Anh/chị cần đúng hàm lượng này phải không ạ? Kho tổng vừa tìm được hộp cuối cùng nhưng đang có người hỏi mua; vui lòng {requested_action} để em ưu tiên đơn của mình.",
        "Bên em đã giữ tạm thuốc theo tên anh/chị, tuy nhiên quy định hàng hiếm phải chốt thanh toán trước khi xuất kho. Anh/chị {requested_action} trong ít phút tới, nếu quá giờ hệ thống tự nhả hàng.",
    ),
    "insurance-claim-inspection": (
        "Tôi là giám định viên xử lý hồ sơ bồi thường của anh/chị. Quyết định đã duyệt nhưng còn thiếu chứng nhận hiện trường; anh/chị {requested_action} trong hôm nay, trước khi hệ thống đóng hồ sơ.",
        "Hồ sơ tai nạn của anh/chị đã qua thẩm định và đang chờ bước bổ sung cuối. Vui lòng {requested_action}; quá 17 giờ hệ thống sẽ đóng yêu cầu bồi thường.",
        "Tôi vừa gửi hóa đơn cho dịch vụ xác nhận hiện trường bắt buộc trước khi chi trả. Anh/chị {requested_action} ngay; tôi sẽ ký hoàn tất hồ sơ trong ca này.",
        "Khoản bồi thường đã sẵn sàng chuyển nhưng bộ phận kiểm soát yêu cầu thêm biên bản giám định. Anh/chị {requested_action}, tôi sẽ cập nhật chứng nhận và giải ngân trước cuối ngày.",
        "Anh/chị đang ở bước cuối của hồ sơ bảo hiểm, đừng để yêu cầu bị hủy vì thiếu phí kiểm tra. Anh/chị {requested_action} giúp tôi hôm nay, sau đó tôi gửi lịch chi trả ngay.",
    ),
    "charity-beneficiary-transfer": (
        "Quỹ đang bảo trì cổng quyên góp, trong khi gia đình trong hồ sơ tôi gửi cần đóng viện phí tối nay. Nếu anh/chị muốn hỗ trợ kịp thời, xin {requested_action} để tôi chuyển ngay cho bệnh viện.",
        "Em đang điều phối ca bệnh của bé trong hình, bệnh viện yêu cầu gia đình hoàn tất viện phí trước ca mổ. Hệ thống quỹ chưa hoạt động lại nên anh/chị {requested_action} giúp em trong tối nay.",
        "Cảm ơn anh/chị đã quan tâm đến gia đình này. Khoản hỗ trợ cần đến trước giờ bệnh viện chốt sổ, vui lòng {requested_action}; em sẽ gửi thư xác nhận sau khi tiếp nhận.",
        "Tối nay quỹ phải gom đủ viện phí cho trường hợp khẩn cấp vừa gửi anh/chị. Do cổng chung đang lỗi, mong anh/chị {requested_action} để khoản cứu trợ không bị chậm.",
        "Gia đình còn thiếu một phần chi phí điều trị và thời hạn thanh toán chỉ còn vài giờ. Anh/chị {requested_action} trực tiếp qua em, quỹ sẽ cập nhật tên mình vào danh sách nhà hảo tâm sau.",
    ),
    "pet-adoption-transport": (
        "Bé đã kiểm tra sức khỏe xong và có thể về với anh/chị hôm nay. Xe cứu hộ sắp rời trạm, anh/chị {requested_action} để bên em chuẩn bị lồng và giữ chỗ vận chuyển.",
        "Em gửi video mới của bé để anh/chị yên tâm nhé. Đơn vị vận chuyển yêu cầu chốt lồng chuyên dụng trước giờ xuất phát, mình {requested_action} ngay để bé kịp chuyến.",
        "Hồ sơ nhận nuôi của anh/chị đã được trạm duyệt, chỉ còn phí đưa bé về và thuê lồng an toàn. Anh/chị {requested_action}; xe sẽ chạy trong ít phút nữa.",
        "Bé đang chờ tại điểm tập kết và tài xế chỉ nhận vận chuyển khi có lồng đúng chuẩn. Anh/chị {requested_action} giúp em trước khi họ đóng chuyến, nếu lỡ phải chờ sang tuần.",
        "Trạm đã giữ bé theo tên anh/chị nhưng hôm nay xe chỉ còn một vị trí. Để hoàn tất bàn giao, vui lòng {requested_action} ngay, bên em sẽ gửi lịch giao sau khi xác nhận.",
    ),
    "travel-ticket-reissue": (
        "Chào anh/chị, chặng bay trong mã đặt chỗ của mình vừa bị hủy và hãng yêu cầu bù chênh lệch để cấp vé mới. Giá giữ chỗ còn hai mươi phút, anh/chị {requested_action} ngay giúp em.",
        "Em đang xử lý lại vé cho anh/chị vì lịch trình cũ không còn khai thác. Hãng đã giữ một chuyến thay thế nhưng sắp nhả chỗ, vui lòng {requested_action} để xuất vé mới.",
        "Mã đặt chỗ của anh/chị đã được chuyển sang chuyến kế tiếp, chỉ còn thiếu khoản chênh lệch. Anh/chị {requested_action} trong hai mươi phút, quá thời gian giá sẽ đổi và chỗ bị hủy.",
        "Đại lý vừa nhận thông báo hủy chặng của vé mình. Anh/chị {requested_action} ngay để giữ đúng hành trình thay thế trước khi hệ thống đóng phiên.",
        "Anh/chị xác nhận đổi vé sớm giúp em nhé, chuyến cũ không thể sử dụng và hãng chỉ bảo lưu mức giá hiện tại trong ít phút. Mình {requested_action} để em phát hành lại ngay.",
    ),
    "hotel-relocation-deposit": (
        "Khách sạn xin lỗi vì phòng anh/chị đặt đang phải đóng do sự cố đường nước. Tôi đã giữ phòng tương đương tại cơ sở đối tác, anh/chị {requested_action} trong mười phút tới; nếu chậm họ sẽ nhả phòng.",
        "Đặt phòng của anh/chị cần chuyển sang khách sạn gần đó vì khu nhà hiện tại không thể đón khách. Phòng cuối đang được giữ tạm; vui lòng {requested_action} ngay.",
        "Tôi là quản lý ca tối và đang hỗ trợ đổi nơi lưu trú cho anh/chị. Cơ sở đối tác yêu cầu cọc riêng trước khi bàn giao phòng; anh/chị {requested_action}, quá mười phút họ sẽ bán phòng.",
        "Phòng trong xác nhận cũ vừa phát sinh lỗi kỹ thuật nên chúng tôi đã bố trí hạng phòng cao hơn ở khách sạn bên cạnh. Anh/chị {requested_action} ngay trước khi phương án cuối cùng hết hiệu lực.",
        "Anh/chị phản hồi gấp giúp tôi: khách sạn không còn phòng hoạt động tối nay, còn đối tác chỉ giữ chỗ mới trong ít phút. Vui lòng {requested_action} rồi tôi gửi xác nhận nhận phòng cập nhật.",
    ),
    "tour-group-emergency": (
        "Xe của đoàn đang bị giữ tại cửa khẩu vì thiếu khoản bảo lãnh phát sinh. Anh/chị {requested_action} ngay giúp tôi; nếu không đủ tiền trong ít phút nữa, chúng ta sẽ lỡ toàn bộ lịch trình.",
        "Tôi đang làm việc với phía cửa khẩu nhưng họ chưa cho xe đi tiếp cho đến khi nộp đủ phí bảo lãnh. Mỗi thành viên vui lòng {requested_action}; xử lý chậm đoàn sẽ mắc lại qua đêm.",
        "Anh/chị hỗ trợ gấp phần đóng góp của mình nhé, xe đoàn hiện chưa được thông quan và lịch tham quan sắp bắt đầu. Hãy {requested_action} để tôi gom đủ khoản bảo lãnh ngay.",
        "Đoàn phát sinh sự cố giấy tờ ở biên giới, bên quản lý yêu cầu bảo lãnh trước khi trả xe. Anh/chị {requested_action} trong lúc tôi hoàn thiện thủ tục, chậm nữa sẽ mất các dịch vụ đã đặt.",
        "Mọi người đang chờ trên xe và tôi cần hoàn tất khoản bảo lãnh để tiếp tục hành trình. Anh/chị {requested_action} ngay giúp tôi; đủ tiền tôi sẽ xử lý cho đoàn đi liền.",
    ),
    "airline-baggage-compensation": (
        "Tôi phụ trách hành lý thất lạc của anh/chị, kiện đồ đã được tìm thấy và hãng đang chuẩn bị khoản bồi thường. Anh/chị {requested_action} trong hôm nay để xác minh tài khoản nhận tiền.",
        "Hãng đã đối chiếu xong biên bản hành lý của anh/chị và có thể chi trả ngay. Vui lòng {requested_action}; yêu cầu sẽ tự đóng cuối ngày nếu chưa đủ thông tin.",
        "Tin vui là hành lý của anh/chị đã về kho, đồng thời hồ sơ được duyệt bồi thường chậm giao. Anh/chị {requested_action} để bộ phận tài chính chuyển tiền trước khi phiên hết hạn.",
        "Tôi đang hoàn tất vụ việc hành lý theo mã của anh/chị. Cổng bồi thường cần kiểm tra thẻ nhận tiền, xin {requested_action} ngay; quá hôm nay hồ sơ phải mở lại từ đầu.",
        "Khoản bồi thường hành lý đã có lệnh chi nhưng còn thiếu xác nhận phương thức nhận. Anh/chị {requested_action} ngay hôm nay; hoàn tất xong tôi sẽ báo lịch giao lại kiện đồ.",
    ),
}
