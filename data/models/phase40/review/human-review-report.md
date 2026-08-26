# Phase 40 Vietnamese Validation Review

Vietnamese-fluent reviewer attestation: **confirmed**

The review is observational only. Frozen labels, predictions, raw outputs, metrics, safety gates, and checkpoint selection were not edited.

## Overall summary

Reviewed rows: 52

Assessment counts:
- `prediction_supported`: 46
- `prediction_unsupported`: 4
- `gold_label_concern`: 1
- `ambiguous`: 1

Disagreement indicators:
- `frozen_prediction_differs_from_gold`: 5
- `reviewer_prediction_unsupported`: 4
- `reviewer_gold_label_concern`: 1
- `reviewer_ambiguous`: 1

Mechanism observations:
- 2 x "Dự đoán không phù hợp vì đây có thể là chương trình giới thiệu hợp lệ qua tên miền chính thức của Binance, không yêu cầu đặt cọc, chuyển tiền hoặc cung cấp thông tin nhạy cảm. Việc trả hoa hồng giới thiệu chưa đủ để kết luận là lừa đảo nhiệm vụ."
- 2 x "Dự đoán phù hợp vì người gửi dùng vỏ bọc kiện hàng và thuế thông quan để ép người nhận nộp tiền vào tài khoản được chỉ định trước hạn chót, phù hợp với lừa đảo thao túng qua dịch vụ giao nhận."
- 2 x "Dự đoán phù hợp vì người gửi hứa hoàn tiền và hoa hồng cho nhiệm vụ mua hàng, đánh giá sản phẩm nhưng yêu cầu chuyển tiền trước, đúng mô thức lừa đảo đơn hàng."
- 2 x "Dự đoán phù hợp vì người gửi tự xưng là ACB, dùng cảnh báo truy cập trái phép để thúc người nhận xác minh OTP, đúng cơ chế mạo danh ngân hàng và tạo áp lực bảo mật."
- 2 x "Dự đoán phù hợp vì tin nhắn mạo danh TPBank và yêu cầu gọi số cá nhân để cung cấp OTP dưới lý do khóa tài khoản khẩn cấp, đúng cơ chế chiếm đoạt thông tin xác thực ngân hàng."
- 2 x "Dự đoán phù hợp vì đây chỉ là thông báo đã gửi OTP cho một lần đăng nhập, không yêu cầu người nhận tiết lộ mã, chuyển tiền hoặc mở liên kết."
- 2 x "Dự đoán phù hợp vì đây là thông báo số dư và lời nhắc quản lý tài khoản thông thường, không có yêu cầu cung cấp thông tin, chuyển tiền hoặc thực hiện hành động rủi ro."
- 1 x "Dự đoán không phù hợp vì người gửi không tự xưng là ngân hàng hay nhân viên ngân hàng mà dùng giọng điệu quen biết, lo lắng và thúc giục để nhờ người nhận xác minh thông tin, phù hợp hơn với thao túng xã hội."
- 1 x "Dự đoán không phù hợp vì đây có thể là thông báo OTP giao dịch thông thường, yêu cầu người dùng tự nhập mã và không đề nghị gửi mã cho người khác hoặc truy cập liên kết. Số điện thoại liên hệ tạo chút nghi ngờ nhưng chưa đủ để xác lập hành vi mạo danh ngân hàng."
- 1 x "Dự đoán phù hợp vì lời mời hứa hoa hồng giới thiệu nhưng yêu cầu nộp phí xác minh trước để kích hoạt tài khoản, đúng mô thức thưởng nhiệm vụ kèm phí ứng trước."
- 1 x "Dự đoán phù hợp vì lời mời làm nhiệm vụ like, follow và bình luận để nhận tiền theo từng task, kèm yêu cầu chuyển sang Zalo và dồn thanh toán sau 100 task, phù hợp với mô thức lừa đảo nhiệm vụ."
- 1 x "Dự đoán phù hợp vì người gửi dùng lý do bảo vệ nhóm và hạn mười phút để thúc ép quét mã QR gắn với tài khoản, phù hợp với thao túng xã hội nhằm chiếm quyền tài khoản."
- 1 x "Dự đoán phù hợp vì người gửi mạo danh hỗ trợ viên Techcombank, tạo giao dịch giả và áp lực 30 phút để dụ đăng nhập vào tên miền đáng ngờ rồi nhập Smart OTP."
- 1 x "Dự đoán phù hợp vì người gửi mạo danh nhân viên Vietcombank và yêu cầu truy cập một tên miền không chính thức để cập nhật thông tin tài khoản."
- 1 x "Dự đoán phù hợp vì người gửi mạo danh quản lý dự án Binance, dùng tên miền giả và lời hứa hoa hồng, lợi nhuận cao để lôi kéo vào chương trình giới thiệu đáng ngờ."
- 1 x "Dự đoán phù hợp vì người gửi mời làm các nhiệm vụ like, follow và bình luận để nhận tiền theo từng task, đồng thời dẫn tới liên kết đáng ngờ và thúc ép đăng ký nhanh."
- 1 x "Dự đoán phù hợp vì người gửi tuyển người đặt đơn hàng ảo để tăng xếp hạng và hứa trả hoa hồng theo từng đơn, đúng mô thức lừa đảo làm nhiệm vụ."
- 1 x "Dự đoán phù hợp vì người gửi tuyển đặt đơn hàng ảo để nhận hoa hồng nhưng yêu cầu chuyển trước 100.000 đồng để nâng cấp tài khoản, đúng cơ chế lừa đảo nhiệm vụ."
- 1 x "Dự đoán phù hợp vì người gửi tuyển đặt đơn hàng ảo để nhận tiền theo từng đơn nhưng buộc chuyển trước 200.000 đồng, đúng cơ chế lừa đảo nhiệm vụ kèm khoản ứng trước."
- 1 x "Dự đoán phù hợp vì người gửi tự nhận là cán bộ kỹ thuật BIDV, tạo áp lực cập nhật gấp và xin OTP để thao tác từ xa, đúng cơ chế mạo danh ngân hàng nhằm lấy thông tin xác thực."
- 1 x "Dự đoán phù hợp vì người gửi tự nhận là nhân viên Vietcombank, viện cớ tài khoản bị khóa và dẫn người nhận tới tên miền giả để kích hoạt lại, đúng cơ chế mạo danh ngân hàng."
- 1 x "Dự đoán phù hợp vì người gửi tự nhận là trợ lý nhóm đầu tư kín, dùng sự khan hiếm và quyền tiếp cận tín hiệu mua để thúc người nhận chuyển tiền đặt cọc."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng bộ phận bảo mật Techcombank và yêu cầu cung cấp OTP qua số điện thoại để hủy giao dịch, đúng thủ đoạn chiếm đoạt thông tin ngân hàng."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng là nhân viên VPBank, dẫn người nhận đến tên miền đáng ngờ để đổi mật khẩu và đe dọa khóa tài khoản, đúng cơ chế mạo danh ngân hàng."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng là tư vấn viên Agribank và yêu cầu nhập CCCD cùng mã PIN trên tên miền đáng ngờ để mở khóa tài khoản, đúng cơ chế mạo danh ngân hàng nhằm lấy thông tin nhạy cảm."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng nhân viên Techcombank, dùng giao dịch lạ để gây hoảng sợ rồi yêu cầu đăng nhập qua liên kết giả nhằm xác thực Smart OTP."
- 1 x "Dự đoán phù hợp vì người gửi viện cớ dùng số mới, tự nhận phụ trách tiền mừng cưới rồi thúc mọi người chuyển tiền qua mã QR, có dấu hiệu mạo danh quan hệ và gây áp lực thời gian."
- 1 x "Dự đoán phù hợp vì nội dung cung cấp OTP để người dùng tự nhập trong ứng dụng nhằm xác minh giao dịch, không yêu cầu gửi mã cho người khác hoặc truy cập liên kết."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh BIDV, viện cớ Smart OTP sắp hết hạn và thúc ép truy cập liên kết không chính thức dưới nguy cơ tài khoản bị tạm ngưng."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh MB Bank, viện dẫn quy định eKYC và nguy cơ khóa tài khoản để ép người nhận truy cập liên kết đáng ngờ."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh Vietcombank, dùng cảnh báo đăng nhập lạ và áp lực khẩn cấp để dụ người nhận truy cập liên kết giả nhằm xác nhận tài khoản."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh Vietcombank, dẫn đến tên miền đáng ngờ để xác thực tài khoản và đe dọa khóa tài khoản trong thời gian rất ngắn."
- 1 x "Dự đoán phù hợp vì đây chỉ là thông báo giao dịch đã hoàn tất, không yêu cầu chuyển thêm tiền, cung cấp thông tin nhạy cảm hoặc truy cập liên kết."
- 1 x "Dự đoán phù hợp vì đây có thể là thông báo cập nhật ứng dụng thông thường; tin nhắn không đưa liên kết lạ và không đòi thông tin đăng nhập, mã OTP hoặc tiền."
- 1 x "Dự đoán phù hợp vì đây là mô hình làm đơn hàng ảo nhận hoa hồng và buộc người tham gia chuyển trước 200.000 đồng để nâng cấp tài khoản, đúng cơ chế lừa đảo nhiệm vụ."
- 1 x "Dự đoán phù hợp vì đây là thông báo OTP giao dịch thông thường, yêu cầu người dùng tự nhập mã trong ứng dụng Smart OTP và không yêu cầu tiết lộ mã cho người khác."
- 1 x "Dự đoán phù hợp vì đây là thông báo OTP phục vụ đăng nhập và còn nhắc người nhận không chia sẻ mã, không có hành vi thu thập thông tin nhạy cảm."
- 1 x "Dự đoán phù hợp vì đây là thông báo OTP đăng nhập hợp lệ và còn cảnh báo không chia sẻ mã, không có hành vi thu thập thông tin hoặc thúc ép thao tác nguy hiểm."
- 1 x "Dự đoán phù hợp vì đây là thông báo cập nhật ứng dụng thông thường, không kèm liên kết đáng ngờ, yêu cầu cung cấp thông tin xác thực hoặc chuyển tiền."
- 1 x "Dự đoán phù hợp vì đây là thông báo lịch bảo trì Internet Banking thông thường, không kèm yêu cầu chuyển tiền, cung cấp thông tin nhạy cảm hoặc truy cập liên kết."
- 1 x "Dự đoán phù hợp vì đây là thông báo số dư kèm khuyến nghị quản lý tài khoản chung, không có liên kết, yêu cầu cung cấp thông tin hoặc chuyển tiền."
- 1 x "Dự đoán phù hợp vì đây là thông báo tiền vào thông thường và chỉ hướng dẫn kiểm tra trong ứng dụng Internet Banking, không có liên kết lạ hoặc yêu cầu cung cấp thông tin."
- 1 x "Dự đoán phù hợp vì đây là tin nhắn cấp OTP thông thường, chỉ yêu cầu nhập mã trong ứng dụng và không yêu cầu gửi mã cho người khác, chuyển tiền hoặc mở liên kết."
- 1 x "Nhãn vàng đáng lo ngại vì người gửi trực tiếp không tự nhận là MB Bank hay nhân viên ngân hàng mà đóng vai người quen giới thiệu một nhóm “hỗ trợ” và dụ nạn nhân cho điều khiển điện thoại từ xa. Cơ chế chính phù hợp hơn với thao túng xã hội dựa trên quan hệ và sự tin cậy."
- 1 x "Yêu cầu đặt cọc phí trước khi được kiểm tra xe có thể là thủ đoạn dịch vụ nhằm thu tiền ứng trước. Tuy nhiên, đây cũng có thể là chính sách điều chuyển xe hợp lệ nên cả zalo_social_engineering và benign đều có cơ sở."

Shortcut-pattern observations:
- 2 x "Mô hình có thể đã dựa quá nhiều vào các từ “hoa hồng” và “giới thiệu” dù không có phí ứng trước hoặc liên kết giả mạo."
- 1 x "Mô hình có thể đã dựa nhiều vào các từ “đặt cọc” và “phí” dù nội dung chưa chứng minh có giả mạo hoặc gian dối."
- 1 x "Mô hình có thể đã dựa quá nhiều vào các từ “OTP”, “giao dịch” và số điện thoại liên hệ."
- 1 x "Mô hình có thể đã dựa quá nhiều vào cụm từ “tài khoản ngân hàng” mà bỏ qua danh tính và quan hệ do người gửi thể hiện."

## Per-model summary

### `phase40-qwen-qlora-full-seed42-v1`

Reviewed rows: 26

Assessment counts:
- `prediction_supported`: 23
- `prediction_unsupported`: 1
- `gold_label_concern`: 1
- `ambiguous`: 1

Disagreement indicators:
- `frozen_prediction_differs_from_gold`: 2
- `reviewer_prediction_unsupported`: 1
- `reviewer_gold_label_concern`: 1
- `reviewer_ambiguous`: 1

Mechanism observations:
- 1 x "Dự đoán không phù hợp vì đây có thể là chương trình giới thiệu hợp lệ qua tên miền chính thức của Binance, không yêu cầu đặt cọc, chuyển tiền hoặc cung cấp thông tin nhạy cảm. Việc trả hoa hồng giới thiệu chưa đủ để kết luận là lừa đảo nhiệm vụ."
- 1 x "Dự đoán phù hợp vì lời mời hứa hoa hồng giới thiệu nhưng yêu cầu nộp phí xác minh trước để kích hoạt tài khoản, đúng mô thức thưởng nhiệm vụ kèm phí ứng trước."
- 1 x "Dự đoán phù hợp vì lời mời làm nhiệm vụ like, follow và bình luận để nhận tiền theo từng task, kèm yêu cầu chuyển sang Zalo và dồn thanh toán sau 100 task, phù hợp với mô thức lừa đảo nhiệm vụ."
- 1 x "Dự đoán phù hợp vì người gửi dùng lý do bảo vệ nhóm và hạn mười phút để thúc ép quét mã QR gắn với tài khoản, phù hợp với thao túng xã hội nhằm chiếm quyền tài khoản."
- 1 x "Dự đoán phù hợp vì người gửi dùng vỏ bọc kiện hàng và thuế thông quan để ép người nhận nộp tiền vào tài khoản được chỉ định trước hạn chót, phù hợp với lừa đảo thao túng qua dịch vụ giao nhận."
- 1 x "Dự đoán phù hợp vì người gửi hứa hoàn tiền và hoa hồng cho nhiệm vụ mua hàng, đánh giá sản phẩm nhưng yêu cầu chuyển tiền trước, đúng mô thức lừa đảo đơn hàng."
- 1 x "Dự đoán phù hợp vì người gửi mạo danh hỗ trợ viên Techcombank, tạo giao dịch giả và áp lực 30 phút để dụ đăng nhập vào tên miền đáng ngờ rồi nhập Smart OTP."
- 1 x "Dự đoán phù hợp vì người gửi mời làm các nhiệm vụ like, follow và bình luận để nhận tiền theo từng task, đồng thời dẫn tới liên kết đáng ngờ và thúc ép đăng ký nhanh."
- 1 x "Dự đoán phù hợp vì người gửi tuyển người đặt đơn hàng ảo để tăng xếp hạng và hứa trả hoa hồng theo từng đơn, đúng mô thức lừa đảo làm nhiệm vụ."
- 1 x "Dự đoán phù hợp vì người gửi tự nhận là cán bộ kỹ thuật BIDV, tạo áp lực cập nhật gấp và xin OTP để thao tác từ xa, đúng cơ chế mạo danh ngân hàng nhằm lấy thông tin xác thực."
- 1 x "Dự đoán phù hợp vì người gửi tự nhận là nhân viên Vietcombank, viện cớ tài khoản bị khóa và dẫn người nhận tới tên miền giả để kích hoạt lại, đúng cơ chế mạo danh ngân hàng."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng là ACB, dùng cảnh báo truy cập trái phép để thúc người nhận xác minh OTP, đúng cơ chế mạo danh ngân hàng và tạo áp lực bảo mật."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng là nhân viên VPBank, dẫn người nhận đến tên miền đáng ngờ để đổi mật khẩu và đe dọa khóa tài khoản, đúng cơ chế mạo danh ngân hàng."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng là tư vấn viên Agribank và yêu cầu nhập CCCD cùng mã PIN trên tên miền đáng ngờ để mở khóa tài khoản, đúng cơ chế mạo danh ngân hàng nhằm lấy thông tin nhạy cảm."
- 1 x "Dự đoán phù hợp vì nội dung cung cấp OTP để người dùng tự nhập trong ứng dụng nhằm xác minh giao dịch, không yêu cầu gửi mã cho người khác hoặc truy cập liên kết."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh BIDV, viện cớ Smart OTP sắp hết hạn và thúc ép truy cập liên kết không chính thức dưới nguy cơ tài khoản bị tạm ngưng."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh TPBank và yêu cầu gọi số cá nhân để cung cấp OTP dưới lý do khóa tài khoản khẩn cấp, đúng cơ chế chiếm đoạt thông tin xác thực ngân hàng."
- 1 x "Dự đoán phù hợp vì đây chỉ là thông báo đã gửi OTP cho một lần đăng nhập, không yêu cầu người nhận tiết lộ mã, chuyển tiền hoặc mở liên kết."
- 1 x "Dự đoán phù hợp vì đây có thể là thông báo cập nhật ứng dụng thông thường; tin nhắn không đưa liên kết lạ và không đòi thông tin đăng nhập, mã OTP hoặc tiền."
- 1 x "Dự đoán phù hợp vì đây là thông báo OTP đăng nhập hợp lệ và còn cảnh báo không chia sẻ mã, không có hành vi thu thập thông tin hoặc thúc ép thao tác nguy hiểm."
- 1 x "Dự đoán phù hợp vì đây là thông báo cập nhật ứng dụng thông thường, không kèm liên kết đáng ngờ, yêu cầu cung cấp thông tin xác thực hoặc chuyển tiền."
- 1 x "Dự đoán phù hợp vì đây là thông báo lịch bảo trì Internet Banking thông thường, không kèm yêu cầu chuyển tiền, cung cấp thông tin nhạy cảm hoặc truy cập liên kết."
- 1 x "Dự đoán phù hợp vì đây là thông báo số dư và lời nhắc quản lý tài khoản thông thường, không có yêu cầu cung cấp thông tin, chuyển tiền hoặc thực hiện hành động rủi ro."
- 1 x "Dự đoán phù hợp vì đây là tin nhắn cấp OTP thông thường, chỉ yêu cầu nhập mã trong ứng dụng và không yêu cầu gửi mã cho người khác, chuyển tiền hoặc mở liên kết."
- 1 x "Nhãn vàng đáng lo ngại vì người gửi trực tiếp không tự nhận là MB Bank hay nhân viên ngân hàng mà đóng vai người quen giới thiệu một nhóm “hỗ trợ” và dụ nạn nhân cho điều khiển điện thoại từ xa. Cơ chế chính phù hợp hơn với thao túng xã hội dựa trên quan hệ và sự tin cậy."
- 1 x "Yêu cầu đặt cọc phí trước khi được kiểm tra xe có thể là thủ đoạn dịch vụ nhằm thu tiền ứng trước. Tuy nhiên, đây cũng có thể là chính sách điều chuyển xe hợp lệ nên cả zalo_social_engineering và benign đều có cơ sở."

Shortcut-pattern observations:
- 1 x "Mô hình có thể đã dựa nhiều vào các từ “đặt cọc” và “phí” dù nội dung chưa chứng minh có giả mạo hoặc gian dối."
- 1 x "Mô hình có thể đã dựa quá nhiều vào các từ “hoa hồng” và “giới thiệu” dù không có phí ứng trước hoặc liên kết giả mạo."

### `phase40-phobert-full-seed42-v12`

Reviewed rows: 26

Assessment counts:
- `prediction_supported`: 23
- `prediction_unsupported`: 3
- `gold_label_concern`: 0
- `ambiguous`: 0

Disagreement indicators:
- `frozen_prediction_differs_from_gold`: 3
- `reviewer_prediction_unsupported`: 3
- `reviewer_gold_label_concern`: 0
- `reviewer_ambiguous`: 0

Mechanism observations:
- 1 x "Dự đoán không phù hợp vì người gửi không tự xưng là ngân hàng hay nhân viên ngân hàng mà dùng giọng điệu quen biết, lo lắng và thúc giục để nhờ người nhận xác minh thông tin, phù hợp hơn với thao túng xã hội."
- 1 x "Dự đoán không phù hợp vì đây có thể là chương trình giới thiệu hợp lệ qua tên miền chính thức của Binance, không yêu cầu đặt cọc, chuyển tiền hoặc cung cấp thông tin nhạy cảm. Việc trả hoa hồng giới thiệu chưa đủ để kết luận là lừa đảo nhiệm vụ."
- 1 x "Dự đoán không phù hợp vì đây có thể là thông báo OTP giao dịch thông thường, yêu cầu người dùng tự nhập mã và không đề nghị gửi mã cho người khác hoặc truy cập liên kết. Số điện thoại liên hệ tạo chút nghi ngờ nhưng chưa đủ để xác lập hành vi mạo danh ngân hàng."
- 1 x "Dự đoán phù hợp vì người gửi dùng vỏ bọc kiện hàng và thuế thông quan để ép người nhận nộp tiền vào tài khoản được chỉ định trước hạn chót, phù hợp với lừa đảo thao túng qua dịch vụ giao nhận."
- 1 x "Dự đoán phù hợp vì người gửi hứa hoàn tiền và hoa hồng cho nhiệm vụ mua hàng, đánh giá sản phẩm nhưng yêu cầu chuyển tiền trước, đúng mô thức lừa đảo đơn hàng."
- 1 x "Dự đoán phù hợp vì người gửi mạo danh nhân viên Vietcombank và yêu cầu truy cập một tên miền không chính thức để cập nhật thông tin tài khoản."
- 1 x "Dự đoán phù hợp vì người gửi mạo danh quản lý dự án Binance, dùng tên miền giả và lời hứa hoa hồng, lợi nhuận cao để lôi kéo vào chương trình giới thiệu đáng ngờ."
- 1 x "Dự đoán phù hợp vì người gửi tuyển đặt đơn hàng ảo để nhận hoa hồng nhưng yêu cầu chuyển trước 100.000 đồng để nâng cấp tài khoản, đúng cơ chế lừa đảo nhiệm vụ."
- 1 x "Dự đoán phù hợp vì người gửi tuyển đặt đơn hàng ảo để nhận tiền theo từng đơn nhưng buộc chuyển trước 200.000 đồng, đúng cơ chế lừa đảo nhiệm vụ kèm khoản ứng trước."
- 1 x "Dự đoán phù hợp vì người gửi tự nhận là trợ lý nhóm đầu tư kín, dùng sự khan hiếm và quyền tiếp cận tín hiệu mua để thúc người nhận chuyển tiền đặt cọc."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng bộ phận bảo mật Techcombank và yêu cầu cung cấp OTP qua số điện thoại để hủy giao dịch, đúng thủ đoạn chiếm đoạt thông tin ngân hàng."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng là ACB, dùng cảnh báo truy cập trái phép để thúc người nhận xác minh OTP, đúng cơ chế mạo danh ngân hàng và tạo áp lực bảo mật."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng nhân viên Techcombank, dùng giao dịch lạ để gây hoảng sợ rồi yêu cầu đăng nhập qua liên kết giả nhằm xác thực Smart OTP."
- 1 x "Dự đoán phù hợp vì người gửi viện cớ dùng số mới, tự nhận phụ trách tiền mừng cưới rồi thúc mọi người chuyển tiền qua mã QR, có dấu hiệu mạo danh quan hệ và gây áp lực thời gian."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh MB Bank, viện dẫn quy định eKYC và nguy cơ khóa tài khoản để ép người nhận truy cập liên kết đáng ngờ."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh TPBank và yêu cầu gọi số cá nhân để cung cấp OTP dưới lý do khóa tài khoản khẩn cấp, đúng cơ chế chiếm đoạt thông tin xác thực ngân hàng."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh Vietcombank, dùng cảnh báo đăng nhập lạ và áp lực khẩn cấp để dụ người nhận truy cập liên kết giả nhằm xác nhận tài khoản."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh Vietcombank, dẫn đến tên miền đáng ngờ để xác thực tài khoản và đe dọa khóa tài khoản trong thời gian rất ngắn."
- 1 x "Dự đoán phù hợp vì đây chỉ là thông báo giao dịch đã hoàn tất, không yêu cầu chuyển thêm tiền, cung cấp thông tin nhạy cảm hoặc truy cập liên kết."
- 1 x "Dự đoán phù hợp vì đây chỉ là thông báo đã gửi OTP cho một lần đăng nhập, không yêu cầu người nhận tiết lộ mã, chuyển tiền hoặc mở liên kết."
- 1 x "Dự đoán phù hợp vì đây là mô hình làm đơn hàng ảo nhận hoa hồng và buộc người tham gia chuyển trước 200.000 đồng để nâng cấp tài khoản, đúng cơ chế lừa đảo nhiệm vụ."
- 1 x "Dự đoán phù hợp vì đây là thông báo OTP giao dịch thông thường, yêu cầu người dùng tự nhập mã trong ứng dụng Smart OTP và không yêu cầu tiết lộ mã cho người khác."
- 1 x "Dự đoán phù hợp vì đây là thông báo OTP phục vụ đăng nhập và còn nhắc người nhận không chia sẻ mã, không có hành vi thu thập thông tin nhạy cảm."
- 1 x "Dự đoán phù hợp vì đây là thông báo số dư kèm khuyến nghị quản lý tài khoản chung, không có liên kết, yêu cầu cung cấp thông tin hoặc chuyển tiền."
- 1 x "Dự đoán phù hợp vì đây là thông báo số dư và lời nhắc quản lý tài khoản thông thường, không có yêu cầu cung cấp thông tin, chuyển tiền hoặc thực hiện hành động rủi ro."
- 1 x "Dự đoán phù hợp vì đây là thông báo tiền vào thông thường và chỉ hướng dẫn kiểm tra trong ứng dụng Internet Banking, không có liên kết lạ hoặc yêu cầu cung cấp thông tin."

Shortcut-pattern observations:
- 1 x "Mô hình có thể đã dựa quá nhiều vào các từ “OTP”, “giao dịch” và số điện thoại liên hệ."
- 1 x "Mô hình có thể đã dựa quá nhiều vào các từ “hoa hồng” và “giới thiệu” dù không có phí ứng trước hoặc liên kết giả mạo."
- 1 x "Mô hình có thể đã dựa quá nhiều vào cụm từ “tài khoản ngân hàng” mà bỏ qua danh tính và quan hệ do người gửi thể hiện."

## Per-slice summary

### `invalid_output`

Reviewed rows: 0

Assessment counts:
- `prediction_supported`: 0
- `prediction_unsupported`: 0
- `gold_label_concern`: 0
- `ambiguous`: 0

Disagreement indicators:
- `frozen_prediction_differs_from_gold`: 0
- `reviewer_prediction_unsupported`: 0
- `reviewer_gold_label_concern`: 0
- `reviewer_ambiguous`: 0

Mechanism observations:
- None recorded.

Shortcut-pattern observations:
- None recorded.

### `risky_to_benign`

Reviewed rows: 0

Assessment counts:
- `prediction_supported`: 0
- `prediction_unsupported`: 0
- `gold_label_concern`: 0
- `ambiguous`: 0

Disagreement indicators:
- `frozen_prediction_differs_from_gold`: 0
- `reviewer_prediction_unsupported`: 0
- `reviewer_gold_label_concern`: 0
- `reviewer_ambiguous`: 0

Mechanism observations:
- None recorded.

Shortcut-pattern observations:
- None recorded.

### `zalo_involved_misclassification`

Reviewed rows: 2

Assessment counts:
- `prediction_supported`: 0
- `prediction_unsupported`: 1
- `gold_label_concern`: 1
- `ambiguous`: 0

Disagreement indicators:
- `frozen_prediction_differs_from_gold`: 2
- `reviewer_prediction_unsupported`: 1
- `reviewer_gold_label_concern`: 1
- `reviewer_ambiguous`: 0

Mechanism observations:
- 1 x "Dự đoán không phù hợp vì người gửi không tự xưng là ngân hàng hay nhân viên ngân hàng mà dùng giọng điệu quen biết, lo lắng và thúc giục để nhờ người nhận xác minh thông tin, phù hợp hơn với thao túng xã hội."
- 1 x "Nhãn vàng đáng lo ngại vì người gửi trực tiếp không tự nhận là MB Bank hay nhân viên ngân hàng mà đóng vai người quen giới thiệu một nhóm “hỗ trợ” và dụ nạn nhân cho điều khiển điện thoại từ xa. Cơ chế chính phù hợp hơn với thao túng xã hội dựa trên quan hệ và sự tin cậy."

Shortcut-pattern observations:
- 1 x "Mô hình có thể đã dựa quá nhiều vào cụm từ “tài khoản ngân hàng” mà bỏ qua danh tính và quan hệ do người gửi thể hiện."

### `benign_to_risky`

Reviewed rows: 3

Assessment counts:
- `prediction_supported`: 0
- `prediction_unsupported`: 3
- `gold_label_concern`: 0
- `ambiguous`: 0

Disagreement indicators:
- `frozen_prediction_differs_from_gold`: 3
- `reviewer_prediction_unsupported`: 3
- `reviewer_gold_label_concern`: 0
- `reviewer_ambiguous`: 0

Mechanism observations:
- 2 x "Dự đoán không phù hợp vì đây có thể là chương trình giới thiệu hợp lệ qua tên miền chính thức của Binance, không yêu cầu đặt cọc, chuyển tiền hoặc cung cấp thông tin nhạy cảm. Việc trả hoa hồng giới thiệu chưa đủ để kết luận là lừa đảo nhiệm vụ."
- 1 x "Dự đoán không phù hợp vì đây có thể là thông báo OTP giao dịch thông thường, yêu cầu người dùng tự nhập mã và không đề nghị gửi mã cho người khác hoặc truy cập liên kết. Số điện thoại liên hệ tạo chút nghi ngờ nhưng chưa đủ để xác lập hành vi mạo danh ngân hàng."

Shortcut-pattern observations:
- 2 x "Mô hình có thể đã dựa quá nhiều vào các từ “hoa hồng” và “giới thiệu” dù không có phí ứng trước hoặc liên kết giả mạo."
- 1 x "Mô hình có thể đã dựa quá nhiều vào các từ “OTP”, “giao dịch” và số điện thoại liên hệ."

### `risky_cross_confusion`

Reviewed rows: 2

Assessment counts:
- `prediction_supported`: 0
- `prediction_unsupported`: 1
- `gold_label_concern`: 1
- `ambiguous`: 0

Disagreement indicators:
- `frozen_prediction_differs_from_gold`: 2
- `reviewer_prediction_unsupported`: 1
- `reviewer_gold_label_concern`: 1
- `reviewer_ambiguous`: 0

Mechanism observations:
- 1 x "Dự đoán không phù hợp vì người gửi không tự xưng là ngân hàng hay nhân viên ngân hàng mà dùng giọng điệu quen biết, lo lắng và thúc giục để nhờ người nhận xác minh thông tin, phù hợp hơn với thao túng xã hội."
- 1 x "Nhãn vàng đáng lo ngại vì người gửi trực tiếp không tự nhận là MB Bank hay nhân viên ngân hàng mà đóng vai người quen giới thiệu một nhóm “hỗ trợ” và dụ nạn nhân cho điều khiển điện thoại từ xa. Cơ chế chính phù hợp hơn với thao túng xã hội dựa trên quan hệ và sự tin cậy."

Shortcut-pattern observations:
- 1 x "Mô hình có thể đã dựa quá nhiều vào cụm từ “tài khoản ngân hàng” mà bỏ qua danh tính và quan hệ do người gửi thể hiện."

### `correct_calibration_sample`

Reviewed rows: 47

Assessment counts:
- `prediction_supported`: 46
- `prediction_unsupported`: 0
- `gold_label_concern`: 0
- `ambiguous`: 1

Disagreement indicators:
- `frozen_prediction_differs_from_gold`: 0
- `reviewer_prediction_unsupported`: 0
- `reviewer_gold_label_concern`: 0
- `reviewer_ambiguous`: 1

Mechanism observations:
- 2 x "Dự đoán phù hợp vì người gửi dùng vỏ bọc kiện hàng và thuế thông quan để ép người nhận nộp tiền vào tài khoản được chỉ định trước hạn chót, phù hợp với lừa đảo thao túng qua dịch vụ giao nhận."
- 2 x "Dự đoán phù hợp vì người gửi hứa hoàn tiền và hoa hồng cho nhiệm vụ mua hàng, đánh giá sản phẩm nhưng yêu cầu chuyển tiền trước, đúng mô thức lừa đảo đơn hàng."
- 2 x "Dự đoán phù hợp vì người gửi tự xưng là ACB, dùng cảnh báo truy cập trái phép để thúc người nhận xác minh OTP, đúng cơ chế mạo danh ngân hàng và tạo áp lực bảo mật."
- 2 x "Dự đoán phù hợp vì tin nhắn mạo danh TPBank và yêu cầu gọi số cá nhân để cung cấp OTP dưới lý do khóa tài khoản khẩn cấp, đúng cơ chế chiếm đoạt thông tin xác thực ngân hàng."
- 2 x "Dự đoán phù hợp vì đây chỉ là thông báo đã gửi OTP cho một lần đăng nhập, không yêu cầu người nhận tiết lộ mã, chuyển tiền hoặc mở liên kết."
- 2 x "Dự đoán phù hợp vì đây là thông báo số dư và lời nhắc quản lý tài khoản thông thường, không có yêu cầu cung cấp thông tin, chuyển tiền hoặc thực hiện hành động rủi ro."
- 1 x "Dự đoán phù hợp vì lời mời hứa hoa hồng giới thiệu nhưng yêu cầu nộp phí xác minh trước để kích hoạt tài khoản, đúng mô thức thưởng nhiệm vụ kèm phí ứng trước."
- 1 x "Dự đoán phù hợp vì lời mời làm nhiệm vụ like, follow và bình luận để nhận tiền theo từng task, kèm yêu cầu chuyển sang Zalo và dồn thanh toán sau 100 task, phù hợp với mô thức lừa đảo nhiệm vụ."
- 1 x "Dự đoán phù hợp vì người gửi dùng lý do bảo vệ nhóm và hạn mười phút để thúc ép quét mã QR gắn với tài khoản, phù hợp với thao túng xã hội nhằm chiếm quyền tài khoản."
- 1 x "Dự đoán phù hợp vì người gửi mạo danh hỗ trợ viên Techcombank, tạo giao dịch giả và áp lực 30 phút để dụ đăng nhập vào tên miền đáng ngờ rồi nhập Smart OTP."
- 1 x "Dự đoán phù hợp vì người gửi mạo danh nhân viên Vietcombank và yêu cầu truy cập một tên miền không chính thức để cập nhật thông tin tài khoản."
- 1 x "Dự đoán phù hợp vì người gửi mạo danh quản lý dự án Binance, dùng tên miền giả và lời hứa hoa hồng, lợi nhuận cao để lôi kéo vào chương trình giới thiệu đáng ngờ."
- 1 x "Dự đoán phù hợp vì người gửi mời làm các nhiệm vụ like, follow và bình luận để nhận tiền theo từng task, đồng thời dẫn tới liên kết đáng ngờ và thúc ép đăng ký nhanh."
- 1 x "Dự đoán phù hợp vì người gửi tuyển người đặt đơn hàng ảo để tăng xếp hạng và hứa trả hoa hồng theo từng đơn, đúng mô thức lừa đảo làm nhiệm vụ."
- 1 x "Dự đoán phù hợp vì người gửi tuyển đặt đơn hàng ảo để nhận hoa hồng nhưng yêu cầu chuyển trước 100.000 đồng để nâng cấp tài khoản, đúng cơ chế lừa đảo nhiệm vụ."
- 1 x "Dự đoán phù hợp vì người gửi tuyển đặt đơn hàng ảo để nhận tiền theo từng đơn nhưng buộc chuyển trước 200.000 đồng, đúng cơ chế lừa đảo nhiệm vụ kèm khoản ứng trước."
- 1 x "Dự đoán phù hợp vì người gửi tự nhận là cán bộ kỹ thuật BIDV, tạo áp lực cập nhật gấp và xin OTP để thao tác từ xa, đúng cơ chế mạo danh ngân hàng nhằm lấy thông tin xác thực."
- 1 x "Dự đoán phù hợp vì người gửi tự nhận là nhân viên Vietcombank, viện cớ tài khoản bị khóa và dẫn người nhận tới tên miền giả để kích hoạt lại, đúng cơ chế mạo danh ngân hàng."
- 1 x "Dự đoán phù hợp vì người gửi tự nhận là trợ lý nhóm đầu tư kín, dùng sự khan hiếm và quyền tiếp cận tín hiệu mua để thúc người nhận chuyển tiền đặt cọc."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng bộ phận bảo mật Techcombank và yêu cầu cung cấp OTP qua số điện thoại để hủy giao dịch, đúng thủ đoạn chiếm đoạt thông tin ngân hàng."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng là nhân viên VPBank, dẫn người nhận đến tên miền đáng ngờ để đổi mật khẩu và đe dọa khóa tài khoản, đúng cơ chế mạo danh ngân hàng."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng là tư vấn viên Agribank và yêu cầu nhập CCCD cùng mã PIN trên tên miền đáng ngờ để mở khóa tài khoản, đúng cơ chế mạo danh ngân hàng nhằm lấy thông tin nhạy cảm."
- 1 x "Dự đoán phù hợp vì người gửi tự xưng nhân viên Techcombank, dùng giao dịch lạ để gây hoảng sợ rồi yêu cầu đăng nhập qua liên kết giả nhằm xác thực Smart OTP."
- 1 x "Dự đoán phù hợp vì người gửi viện cớ dùng số mới, tự nhận phụ trách tiền mừng cưới rồi thúc mọi người chuyển tiền qua mã QR, có dấu hiệu mạo danh quan hệ và gây áp lực thời gian."
- 1 x "Dự đoán phù hợp vì nội dung cung cấp OTP để người dùng tự nhập trong ứng dụng nhằm xác minh giao dịch, không yêu cầu gửi mã cho người khác hoặc truy cập liên kết."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh BIDV, viện cớ Smart OTP sắp hết hạn và thúc ép truy cập liên kết không chính thức dưới nguy cơ tài khoản bị tạm ngưng."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh MB Bank, viện dẫn quy định eKYC và nguy cơ khóa tài khoản để ép người nhận truy cập liên kết đáng ngờ."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh Vietcombank, dùng cảnh báo đăng nhập lạ và áp lực khẩn cấp để dụ người nhận truy cập liên kết giả nhằm xác nhận tài khoản."
- 1 x "Dự đoán phù hợp vì tin nhắn mạo danh Vietcombank, dẫn đến tên miền đáng ngờ để xác thực tài khoản và đe dọa khóa tài khoản trong thời gian rất ngắn."
- 1 x "Dự đoán phù hợp vì đây chỉ là thông báo giao dịch đã hoàn tất, không yêu cầu chuyển thêm tiền, cung cấp thông tin nhạy cảm hoặc truy cập liên kết."
- 1 x "Dự đoán phù hợp vì đây có thể là thông báo cập nhật ứng dụng thông thường; tin nhắn không đưa liên kết lạ và không đòi thông tin đăng nhập, mã OTP hoặc tiền."
- 1 x "Dự đoán phù hợp vì đây là mô hình làm đơn hàng ảo nhận hoa hồng và buộc người tham gia chuyển trước 200.000 đồng để nâng cấp tài khoản, đúng cơ chế lừa đảo nhiệm vụ."
- 1 x "Dự đoán phù hợp vì đây là thông báo OTP giao dịch thông thường, yêu cầu người dùng tự nhập mã trong ứng dụng Smart OTP và không yêu cầu tiết lộ mã cho người khác."
- 1 x "Dự đoán phù hợp vì đây là thông báo OTP phục vụ đăng nhập và còn nhắc người nhận không chia sẻ mã, không có hành vi thu thập thông tin nhạy cảm."
- 1 x "Dự đoán phù hợp vì đây là thông báo OTP đăng nhập hợp lệ và còn cảnh báo không chia sẻ mã, không có hành vi thu thập thông tin hoặc thúc ép thao tác nguy hiểm."
- 1 x "Dự đoán phù hợp vì đây là thông báo cập nhật ứng dụng thông thường, không kèm liên kết đáng ngờ, yêu cầu cung cấp thông tin xác thực hoặc chuyển tiền."
- 1 x "Dự đoán phù hợp vì đây là thông báo lịch bảo trì Internet Banking thông thường, không kèm yêu cầu chuyển tiền, cung cấp thông tin nhạy cảm hoặc truy cập liên kết."
- 1 x "Dự đoán phù hợp vì đây là thông báo số dư kèm khuyến nghị quản lý tài khoản chung, không có liên kết, yêu cầu cung cấp thông tin hoặc chuyển tiền."
- 1 x "Dự đoán phù hợp vì đây là thông báo tiền vào thông thường và chỉ hướng dẫn kiểm tra trong ứng dụng Internet Banking, không có liên kết lạ hoặc yêu cầu cung cấp thông tin."
- 1 x "Dự đoán phù hợp vì đây là tin nhắn cấp OTP thông thường, chỉ yêu cầu nhập mã trong ứng dụng và không yêu cầu gửi mã cho người khác, chuyển tiền hoặc mở liên kết."
- 1 x "Yêu cầu đặt cọc phí trước khi được kiểm tra xe có thể là thủ đoạn dịch vụ nhằm thu tiền ứng trước. Tuy nhiên, đây cũng có thể là chính sách điều chuyển xe hợp lệ nên cả zalo_social_engineering và benign đều có cơ sở."

Shortcut-pattern observations:
- 1 x "Mô hình có thể đã dựa nhiều vào các từ “đặt cọc” và “phí” dù nội dung chưa chứng minh có giả mạo hoặc gian dối."

## Row observations

- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-4e2357a45e6e6131f583e8eaa8f47ee521c2c56ee92569056219dbc43129ca6f`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tự xưng là nhân viên VPBank, dẫn người nhận đến tên miền đáng ngờ để đổi mật khẩu và đe dọa khóa tài khoản, đúng cơ chế mạo danh ngân hàng."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-bb51f6e4c8f9dd6aac00c2888fbe6725ee19dad2c37fcdde0792329cbe0069b4`: **prediction_supported**; mechanism="Dự đoán phù hợp vì tin nhắn mạo danh BIDV, viện cớ Smart OTP sắp hết hạn và thúc ép truy cập liên kết không chính thức dưới nguy cơ tài khoản bị tạm ngưng."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-9c1ec0abdd8ad863cd6630580dd8d980e67f148f349b61ae05c481180a4a454a`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tự xưng là tư vấn viên Agribank và yêu cầu nhập CCCD cùng mã PIN trên tên miền đáng ngờ để mở khóa tài khoản, đúng cơ chế mạo danh ngân hàng nhằm lấy thông tin nhạy cảm."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-c00ebb4c6bb9659f0d87faacc80bf7179f93786e22759240c24fd419e16e98ed`: **prediction_unsupported**; mechanism="Dự đoán không phù hợp vì đây có thể là chương trình giới thiệu hợp lệ qua tên miền chính thức của Binance, không yêu cầu đặt cọc, chuyển tiền hoặc cung cấp thông tin nhạy cảm. Việc trả hoa hồng giới thiệu chưa đủ để kết luận là lừa đảo nhiệm vụ."; shortcut="Mô hình có thể đã dựa quá nhiều vào các từ “hoa hồng” và “giới thiệu” dù không có phí ứng trước hoặc liên kết giả mạo."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-3b1bb51570df2b52d047c55acdf3fa6e5da46e88bb7aa5a63ef8a6f409dd502b`: **prediction_supported**; mechanism="Dự đoán phù hợp vì lời mời làm nhiệm vụ like, follow và bình luận để nhận tiền theo từng task, kèm yêu cầu chuyển sang Zalo và dồn thanh toán sau 100 task, phù hợp với mô thức lừa đảo nhiệm vụ."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-8e506328913214d79534a260afdf01c0c119a8961138cb3d5c68fde32a8fedfc`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây là tin nhắn cấp OTP thông thường, chỉ yêu cầu nhập mã trong ứng dụng và không yêu cầu gửi mã cho người khác, chuyển tiền hoặc mở liên kết."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-121b6184a91e0ff1d0f0459101f65331acd90633c717aed514da465e52ba3b28`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây là thông báo lịch bảo trì Internet Banking thông thường, không kèm yêu cầu chuyển tiền, cung cấp thông tin nhạy cảm hoặc truy cập liên kết."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-97a97edcd29e2bf504b5f88da66458dc2a35cf988c2df7620f81aff23ca315a1`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây có thể là thông báo cập nhật ứng dụng thông thường; tin nhắn không đưa liên kết lạ và không đòi thông tin đăng nhập, mã OTP hoặc tiền."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-36862b0ea6d043857a44de6c685942b64cb34f21be7ffecf213795b6a50bfa96`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây là thông báo OTP đăng nhập hợp lệ và còn cảnh báo không chia sẻ mã, không có hành vi thu thập thông tin hoặc thúc ép thao tác nguy hiểm."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-87e22e1c89eaeb7e12857d502caf6209a092209c14eaa0f895bd6e8ab1f59816`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi dùng lý do bảo vệ nhóm và hạn mười phút để thúc ép quét mã QR gắn với tài khoản, phù hợp với thao túng xã hội nhằm chiếm quyền tài khoản."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-e4d774be3f7ae435469dccff5a44d57590bb6aefd0a9fd2ee0854ae74d99682d`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi dùng vỏ bọc kiện hàng và thuế thông quan để ép người nhận nộp tiền vào tài khoản được chỉ định trước hạn chót, phù hợp với lừa đảo thao túng qua dịch vụ giao nhận."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-068d1174b73bbc6298c7454821c323105cadbf29ff8c1b139ca4a6544bd2e78c`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi mạo danh hỗ trợ viên Techcombank, tạo giao dịch giả và áp lực 30 phút để dụ đăng nhập vào tên miền đáng ngờ rồi nhập Smart OTP."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-2fe081fc06a0fe54629abc987e169ca055bd60c347155afe6ead590d52a73525`: **prediction_supported**; mechanism="Dự đoán phù hợp vì tin nhắn mạo danh TPBank và yêu cầu gọi số cá nhân để cung cấp OTP dưới lý do khóa tài khoản khẩn cấp, đúng cơ chế chiếm đoạt thông tin xác thực ngân hàng."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-b507069da315ce337d8e7715f06812f6f0d3b2ccb1aea4d6046aee6319e6e2d1`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tuyển người đặt đơn hàng ảo để tăng xếp hạng và hứa trả hoa hồng theo từng đơn, đúng mô thức lừa đảo làm nhiệm vụ."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-76b3e1c3a17307b287d9f2aeda7824a5707f3f9e5809a4279c756ed113f54271`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tự nhận là nhân viên Vietcombank, viện cớ tài khoản bị khóa và dẫn người nhận tới tên miền giả để kích hoạt lại, đúng cơ chế mạo danh ngân hàng."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-7438fa7e6a4a4a41cfadb0b118cc9c57e3b267912b6c8b7eccf30d49e3fdd932`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tự nhận là cán bộ kỹ thuật BIDV, tạo áp lực cập nhật gấp và xin OTP để thao tác từ xa, đúng cơ chế mạo danh ngân hàng nhằm lấy thông tin xác thực."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-0f50217d8ac511964f1c752c63ce5a8fb4fb010c90fc89f9e212c4d36f51532e`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tự xưng là ACB, dùng cảnh báo truy cập trái phép để thúc người nhận xác minh OTP, đúng cơ chế mạo danh ngân hàng và tạo áp lực bảo mật."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-abf879561535da044474497da7e287fe69ff1568ba05711dec804e90b8e39881`: **gold_label_concern**; mechanism="Nhãn vàng đáng lo ngại vì người gửi trực tiếp không tự nhận là MB Bank hay nhân viên ngân hàng mà đóng vai người quen giới thiệu một nhóm “hỗ trợ” và dụ nạn nhân cho điều khiển điện thoại từ xa. Cơ chế chính phù hợp hơn với thao túng xã hội dựa trên quan hệ và sự tin cậy."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-288bb7321f6a7b064112179f825024a8963d02462f0cb5e977ab669154870761`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi mời làm các nhiệm vụ like, follow và bình luận để nhận tiền theo từng task, đồng thời dẫn tới liên kết đáng ngờ và thúc ép đăng ký nhanh."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-7564fd55f22c7265ef2ceff33db3d0f0cee4d1ddd31598a0cb36599d8624a1c6`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi hứa hoàn tiền và hoa hồng cho nhiệm vụ mua hàng, đánh giá sản phẩm nhưng yêu cầu chuyển tiền trước, đúng mô thức lừa đảo đơn hàng."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-08d04f1d7e84766b43f6b325fd6fccc1ded5a01013b7f9888dc65fbc9e621876`: **prediction_supported**; mechanism="Dự đoán phù hợp vì lời mời hứa hoa hồng giới thiệu nhưng yêu cầu nộp phí xác minh trước để kích hoạt tài khoản, đúng mô thức thưởng nhiệm vụ kèm phí ứng trước."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-45a433c8d757526a8e559e4713be1e2ba28368ef97828a0bb46ac41c44eaaf78`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây chỉ là thông báo đã gửi OTP cho một lần đăng nhập, không yêu cầu người nhận tiết lộ mã, chuyển tiền hoặc mở liên kết."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-36f5d373923753c971307e5d7eb7595661203a6754ec353a116b1e72dbe438a1`: **prediction_supported**; mechanism="Dự đoán phù hợp vì nội dung cung cấp OTP để người dùng tự nhập trong ứng dụng nhằm xác minh giao dịch, không yêu cầu gửi mã cho người khác hoặc truy cập liên kết."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-76ac996608d0f51097fa058d6e972f312acfc983e1d77cc1b41e1bd59e5a2502`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây là thông báo số dư và lời nhắc quản lý tài khoản thông thường, không có yêu cầu cung cấp thông tin, chuyển tiền hoặc thực hiện hành động rủi ro."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-e47941e958e5ba39b37818b38c685d6efd98fd9d929ee5faaae290852089d70e`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây là thông báo cập nhật ứng dụng thông thường, không kèm liên kết đáng ngờ, yêu cầu cung cấp thông tin xác thực hoặc chuyển tiền."
- `phase40-qwen-qlora-full-seed42-v1` / `p40-row-v1-84707b484fec98a32cd5dab4dbade8849e451848ba81a86d0b3a98ea278de1c4`: **ambiguous**; mechanism="Yêu cầu đặt cọc phí trước khi được kiểm tra xe có thể là thủ đoạn dịch vụ nhằm thu tiền ứng trước. Tuy nhiên, đây cũng có thể là chính sách điều chuyển xe hợp lệ nên cả zalo_social_engineering và benign đều có cơ sở."; shortcut="Mô hình có thể đã dựa nhiều vào các từ “đặt cọc” và “phí” dù nội dung chưa chứng minh có giả mạo hoặc gian dối."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-3d6de09b9cf3361b23b320a31b42eb2556176b7ef835080985a20e56f9e25fdd`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi viện cớ dùng số mới, tự nhận phụ trách tiền mừng cưới rồi thúc mọi người chuyển tiền qua mã QR, có dấu hiệu mạo danh quan hệ và gây áp lực thời gian."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-497f24610e8e7cae8a94e39f4afe3bfac9c1296d288a56bf7b9167f91121c75c`: **prediction_supported**; mechanism="Dự đoán phù hợp vì tin nhắn mạo danh Vietcombank, dẫn đến tên miền đáng ngờ để xác thực tài khoản và đe dọa khóa tài khoản trong thời gian rất ngắn."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-b4c8fbe4e5cf9865aaaa880e78128e3239847c6e4ee684735ef199da84b2d258`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tự xưng nhân viên Techcombank, dùng giao dịch lạ để gây hoảng sợ rồi yêu cầu đăng nhập qua liên kết giả nhằm xác thực Smart OTP."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-c355d3aec3ce9bc6682c17c7f4e2c36ba85cc1c4811e7d832611a3e844e0499a`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi mạo danh nhân viên Vietcombank và yêu cầu truy cập một tên miền không chính thức để cập nhật thông tin tài khoản."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-4cce5b3889fbdf1fc6f50f5a0f93885744cc85abe3fbaac56c509401ebe0a56c`: **prediction_supported**; mechanism="Dự đoán phù hợp vì tin nhắn mạo danh MB Bank, viện dẫn quy định eKYC và nguy cơ khóa tài khoản để ép người nhận truy cập liên kết đáng ngờ."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-437d18c38fc92d0e63799d12d6aaeb1d58177196086049928b174d177891ce9e`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tự xưng bộ phận bảo mật Techcombank và yêu cầu cung cấp OTP qua số điện thoại để hủy giao dịch, đúng thủ đoạn chiếm đoạt thông tin ngân hàng."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-c00ebb4c6bb9659f0d87faacc80bf7179f93786e22759240c24fd419e16e98ed`: **prediction_unsupported**; mechanism="Dự đoán không phù hợp vì đây có thể là chương trình giới thiệu hợp lệ qua tên miền chính thức của Binance, không yêu cầu đặt cọc, chuyển tiền hoặc cung cấp thông tin nhạy cảm. Việc trả hoa hồng giới thiệu chưa đủ để kết luận là lừa đảo nhiệm vụ."; shortcut="Mô hình có thể đã dựa quá nhiều vào các từ “hoa hồng” và “giới thiệu” dù không có phí ứng trước hoặc liên kết giả mạo."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-bef3ef79fe4c712d7eea5c6aeb525fbaa838c84533a19c6b438a38b6ec136041`: **prediction_unsupported**; mechanism="Dự đoán không phù hợp vì người gửi không tự xưng là ngân hàng hay nhân viên ngân hàng mà dùng giọng điệu quen biết, lo lắng và thúc giục để nhờ người nhận xác minh thông tin, phù hợp hơn với thao túng xã hội."; shortcut="Mô hình có thể đã dựa quá nhiều vào cụm từ “tài khoản ngân hàng” mà bỏ qua danh tính và quan hệ do người gửi thể hiện."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-a285995506ba32c2d401bc1515774c4d6105a1dddb260106a5e3cd22d44ecbe6`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi mạo danh quản lý dự án Binance, dùng tên miền giả và lời hứa hoa hồng, lợi nhuận cao để lôi kéo vào chương trình giới thiệu đáng ngờ."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-c87a88bc3ea5e515848c0cf217829fe5e9cea08a18ee46ccd358363a6f7dbabc`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây là mô hình làm đơn hàng ảo nhận hoa hồng và buộc người tham gia chuyển trước 200.000 đồng để nâng cấp tài khoản, đúng cơ chế lừa đảo nhiệm vụ."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-b5e7c17dcc04efb2456c3ffdab344dc1703eba61692b672e2033ece8580eded6`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây chỉ là thông báo giao dịch đã hoàn tất, không yêu cầu chuyển thêm tiền, cung cấp thông tin nhạy cảm hoặc truy cập liên kết."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-438bb86adb139f199b587fa208050a5d45835a0534e73ea67ae8e05f73349860`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây là thông báo OTP phục vụ đăng nhập và còn nhắc người nhận không chia sẻ mã, không có hành vi thu thập thông tin nhạy cảm."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-54f15d06dd34e5a71365cc2795257ec0deb3e363b30ec593be673144119d6887`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây là thông báo số dư kèm khuyến nghị quản lý tài khoản chung, không có liên kết, yêu cầu cung cấp thông tin hoặc chuyển tiền."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-e4d774be3f7ae435469dccff5a44d57590bb6aefd0a9fd2ee0854ae74d99682d`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi dùng vỏ bọc kiện hàng và thuế thông quan để ép người nhận nộp tiền vào tài khoản được chỉ định trước hạn chót, phù hợp với lừa đảo thao túng qua dịch vụ giao nhận."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-1d51504427fe0748af1706e198efb558ca2ef2756acd8351c5dda60043939a71`: **prediction_supported**; mechanism="Dự đoán phù hợp vì tin nhắn mạo danh Vietcombank, dùng cảnh báo đăng nhập lạ và áp lực khẩn cấp để dụ người nhận truy cập liên kết giả nhằm xác nhận tài khoản."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-2fe081fc06a0fe54629abc987e169ca055bd60c347155afe6ead590d52a73525`: **prediction_supported**; mechanism="Dự đoán phù hợp vì tin nhắn mạo danh TPBank và yêu cầu gọi số cá nhân để cung cấp OTP dưới lý do khóa tài khoản khẩn cấp, đúng cơ chế chiếm đoạt thông tin xác thực ngân hàng."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-a3becd38a5cc4bff52967b8c297e894e2c8b694bc37e6bc9a801c19411fff961`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tuyển đặt đơn hàng ảo để nhận tiền theo từng đơn nhưng buộc chuyển trước 200.000 đồng, đúng cơ chế lừa đảo nhiệm vụ kèm khoản ứng trước."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-da18da407ab2227754df8a4b8dfff144689bd15aa1e26a373e8af7688a9e2b56`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tự nhận là trợ lý nhóm đầu tư kín, dùng sự khan hiếm và quyền tiếp cận tín hiệu mua để thúc người nhận chuyển tiền đặt cọc."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-0f50217d8ac511964f1c752c63ce5a8fb4fb010c90fc89f9e212c4d36f51532e`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tự xưng là ACB, dùng cảnh báo truy cập trái phép để thúc người nhận xác minh OTP, đúng cơ chế mạo danh ngân hàng và tạo áp lực bảo mật."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-9604ee0e1be5f90ef34a471c734416c6279ee65ff0a483e6ef65d5e0d293fb7a`: **prediction_unsupported**; mechanism="Dự đoán không phù hợp vì đây có thể là thông báo OTP giao dịch thông thường, yêu cầu người dùng tự nhập mã và không đề nghị gửi mã cho người khác hoặc truy cập liên kết. Số điện thoại liên hệ tạo chút nghi ngờ nhưng chưa đủ để xác lập hành vi mạo danh ngân hàng."; shortcut="Mô hình có thể đã dựa quá nhiều vào các từ “OTP”, “giao dịch” và số điện thoại liên hệ."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-7564fd55f22c7265ef2ceff33db3d0f0cee4d1ddd31598a0cb36599d8624a1c6`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi hứa hoàn tiền và hoa hồng cho nhiệm vụ mua hàng, đánh giá sản phẩm nhưng yêu cầu chuyển tiền trước, đúng mô thức lừa đảo đơn hàng."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-72d32391546d62d1a67977d650b4a98d727a2a51640f8497340e44ed598b54cd`: **prediction_supported**; mechanism="Dự đoán phù hợp vì người gửi tuyển đặt đơn hàng ảo để nhận hoa hồng nhưng yêu cầu chuyển trước 100.000 đồng để nâng cấp tài khoản, đúng cơ chế lừa đảo nhiệm vụ."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-31c139362c04ab9d0b8c9e790f8d6660a162fe69b8ce1245645eefb0e45a5783`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây là thông báo tiền vào thông thường và chỉ hướng dẫn kiểm tra trong ứng dụng Internet Banking, không có liên kết lạ hoặc yêu cầu cung cấp thông tin."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-45a433c8d757526a8e559e4713be1e2ba28368ef97828a0bb46ac41c44eaaf78`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây chỉ là thông báo đã gửi OTP cho một lần đăng nhập, không yêu cầu người nhận tiết lộ mã, chuyển tiền hoặc mở liên kết."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-76ac996608d0f51097fa058d6e972f312acfc983e1d77cc1b41e1bd59e5a2502`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây là thông báo số dư và lời nhắc quản lý tài khoản thông thường, không có yêu cầu cung cấp thông tin, chuyển tiền hoặc thực hiện hành động rủi ro."
- `phase40-phobert-full-seed42-v12` / `p40-row-v1-0d4470734e5c6857cab783debcbbb47884a7e2efdcd5ae0bf679d2536d59ea1a`: **prediction_supported**; mechanism="Dự đoán phù hợp vì đây là thông báo OTP giao dịch thông thường, yêu cầu người dùng tự nhập mã trong ứng dụng Smart OTP và không yêu cầu tiết lộ mã cho người khác."

## Limitations

- `single_training_seed_42_no_variance_or_significance_claim`
- `validation_only_no_held_out_test_claim`
- `zalo_validation_support_is_small_and_all_zalo_errors_require_review`
- `full_lora_cancelled_before_start_after_bounded_local_resource_probe`
- `lora_probe_has_no_predictions_and_supports_no_quality_claim`
- `colab_is_validation_contingency_only_before_held_out_open`

These observations use development validation data and a single training seed; they support no held-out-test, variance, significance, relabeling, or checkpoint-reselection claim.
