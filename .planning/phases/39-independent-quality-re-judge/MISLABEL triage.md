1.Relabel to: bank_impersonation
Notes: Fake ACB login URL used to harvest credentials under threat of account suspension.

2.Drop row
Notes: Obvious synthetic artifact (bracketed placeholder URL syntax [http://...]). Alternatively relabel to government_impersonation_phishing if syntax is retained.

3.Drop row
Notes: Synthetic text artifact using literal placeholder vcb-fake.com and markdown brackets.

4.Drop row
Notes: Unrealistic synthetic placeholder domain fakeURL.com and bracketed formatting.

5.Drop row
Notes: Literal "fakebank.com" domain name breaks realism; a real scammer wouldn't self-label as fake.

6.Drop row
Notes: Bracket-wrapped URL [http://xyz-bank-update.com] reads as unresolved template syntax, not real text.

7.Drop row
Notes: Bracket-wrapped URL [http://ibanking-safe.com] is a generation artifact.

8.Relabel to: bank_impersonation
Notes: Fake "CAFC" tech-support caller pressures a virus-fear callback tied to Internet Banking access; impersonation, not a task lure.

9.Drop row
Notes: Bracket-wrapped WhatsApp Gold URL [http://whatsappgold.vn] is a template artifact.

10.Drop row
Notes: Bracket-wrapped Paychex login URL [http://paychex-login.com] is a template artifact.

11.Drop row
Notes: Bracket-wrapped fake ABC bank URL [https://abc-bank-login.com] is a template artifact.

12.Relabel to: bank_impersonation
Notes: Fake ACB OTP-confirmation link harvesting credentials under threat framing.

13.Drop row
Notes: "fakebank.com" literal naming plus brackets; double synthetic tell.

14.Drop row
Notes: "fakebank.com" literal naming exposes generated placeholder domain.

15.Relabel to: bank_impersonation
Notes: Fake police officer phishes Internet Banking credentials via a bit.ly link, not offering a task.

16.Relabel to: bank_impersonation
Notes: Fake bank "verify" link with account-lock threat; direct phishing, not task fraud.

17.Relabel to: bank_impersonation
Notes: Paychex-themed OTP verification link phishing, framed as payroll pressure.

18.Relabel to: bank_impersonation
Notes: Fake Vietcombank staff directly requests the victim hand over an OTP code.

19.Drop row
Notes: Bracket-wrapped app name and URL ([CCCDUpdateApp], [https://app-cccdupdate.com]) is unresolved template syntax.

20.Relabel to: bank_impersonation
Notes: Fake Tax Office (Cục Thuế) refund pretext driving a phone callback; impersonation phishing, not a task.

21.Relabel to: bank_impersonation
Notes: Fake Vietcombank verification pressure demanding a Smart OTP code, no task element.

22.Relabel to: bank_impersonation
Notes: OTP-harvesting link dressed as bank verification; awkward English sign-off doesn't change the scam mechanism.

23.Relabel to: bank_impersonation
Notes: Fake bank staff phishing for biometric/account update via callback, impersonation not task.

24.Relabel to: bank_impersonation
Notes: Vague "ĐT Ngân hàng" account-update link with lock pressure; generic bank phishing.

25.Relabel to: bank_impersonation
Notes: Fake tech-support/security alert tied to Smart OTP lockout threat; impersonation phishing.

26.Drop row
Notes: Bracket-wrapped WhatsApp upgrade URL [https://upgrade.whatsapp.com] is a template artifact.

27.Drop row
Notes: Bracket-wrapped "Smart OTP admin" URL [https://smartotp-update.com] is a template artifact.

28.Drop row
Notes: Bracket-wrapped Smart OTP app URL [https://smartotp-app.com] is a template artifact.

29.Relabel to: bank_impersonation
Notes: Fake Vietcombank CSKH pressuring immediate account update, phone-only but still institutional phishing.

30.Relabel to: benign
Notes: Reads as a genuine OTP delivery notice (code + expiry, no link, no threat, no request to share it); not a scam.

31.Drop row
Notes: Sequential "0123456789" hotline plus bracketed URL are both obvious placeholders.

32.Drop row
Notes: Bracket-wrapped ACB login URL [http://acb-login.com] is a template artifact.

33.Relabel to: bank_impersonation
Notes: Fake BIDV security team directly solicits an OTP code to "verify identity."

34.Relabel to: bank_impersonation
Notes: Fake VPBank rep pressures an urgent phone callback over a bogus suspicious transaction.

35.Relabel to: bank_impersonation
Notes: Fake BIDV "system upgrade" login link, credential-phishing not task fraud.

36.Drop row
Notes: Bracket-wrapped CCCD update URL [http://cccd-updates.vn] is a template artifact.

37.Drop row
Notes: "smartotp-fake.vn" literal fake naming plus brackets.

38.Relabel to: bank_impersonation
Notes: Fake BIDV callback over a suspicious transaction, phone-only impersonation phishing.

39.Relabel to: benign
Notes: Genuine-style Binance affiliate referral program using the real binance.com domain; not a scam.

40.Relabel to: bank_impersonation
Notes: Generic account-lock reactivation link, phishing pressure not task fraud.

41.Drop row
Notes: Bracket-wrapped "defbank" URL [https://defbank-update.info] is a template artifact.

42.Drop row
Notes: Bracket-wrapped Smart OTP URL [http://smart-otp-update.com] is a template artifact.

43.Relabel to: bank_impersonation
Notes: Fake "CAFC" virus-support callback lure, impersonation phishing not task.

44.Drop row
Notes: Bracket-wrapped WhatsApp Gold URL [http://gold.whatsapp.vn] is a template artifact.

45.Relabel to: bank_impersonation
Notes: Fake Paychex support asks victim to send an OTP to a phone number; payroll-impersonation phishing.

46.Relabel to: bank_impersonation
Notes: Fake BIDV verification link with a 24h deadline; phishing pressure, not task fraud.

47.Relabel to: zalo_social_engineering
Notes: Informal personal plea ("mình"/"bạn", no bank branding) asking a contact to help verify banking info by phone; trust-based social engineering, not institutional phishing or a task.

48.Drop row
Notes: Bracket-wrapped Smart OTP URL [http://secureupdate.com] is a template artifact.

49.Relabel to: bank_impersonation
Notes: Fake police officer invokes a money-laundering case to pressure bank verification by phone.

50.Relabel to: bank_impersonation
Notes: Shopee-branded account-lock alert with lock-now pressure; no link needed to still be phishing.

51.Relabel to: bank_impersonation
Notes: Fake Techcombank verification link over a bogus fraud alert.

52.Drop row
Notes: Bracket-wrapped "[fake-link]" ZaloPay promo is an explicit placeholder.

53.Drop row
Notes: Bracket-wrapped "[fakeURL.com]" investment-scam link is an explicit placeholder.

54.Relabel to: bank_impersonation
Notes: Manufactured "enter OTP now or be locked out" urgency; pressure tactic makes this phishing, not a benign notice.

55.Drop row
Notes: Bracket-wrapped CCCD URL [http://cccdinfo.vn] is a template artifact.

56.Drop row
Notes: "fake-bank.vn" literal naming plus brackets.

57.Drop row
Notes: "fakeLink.vn" literal naming plus brackets.

58.Relabel to: bank_impersonation
Notes: Generic "system error" account-update link, phishing pressure not task fraud.

59.Drop row
Notes: Sequential "0123456789" contact plus bracketed URL, both placeholders.

60.Drop row
Notes: Bracket-wrapped "[www.acb-bank-login.com]" is a template artifact.

61.Drop row
Notes: Bracket-wrapped verify-bank URL [http://verify-bank.com] is a template artifact.

62.Drop row
Notes: Bracket-wrapped "[www.abc-bank-upgrade.com]" is a template artifact.

63.Relabel to: bank_impersonation
Notes: Implausible ACB "reward points" lure still functions as a login-phishing hook, not a task offer.

64.Drop row
Notes: Bracket-wrapped Paychex URL [https://paychexsecure.com] is a template artifact.

65.Drop row
Notes: Bracket-wrapped "xyzbank-upgrade.com" URL is a template artifact.

66.Drop row
Notes: Bracket-wrapped VPBank update URL [https://updateaccount.vn] is a template artifact.

67.Drop row
Notes: Bracket-wrapped "safebanking.vn" URL is a template artifact.

68.Relabel to: bank_impersonation
Notes: Fake Vietcombank staff directly requests a Smart OTP code.

69.Drop row
Notes: "fakebank.com" literal naming plus brackets.

70.Relabel to: bank_impersonation
Notes: Fake BIDV rep pressures phone verification over bogus suspicious transactions.

71.Drop row
Notes: Bracket-wrapped "[fakeURL.vn]" plus an implausible "deposit 10tr get 5tr back" bonus scheme.

72.Drop row
Notes: Sequential "0123456789" contact number is an obvious placeholder.

73.Drop row
Notes: Bracket-wrapped CCCD URL [http://cccdverify.vn] is a template artifact.

74.Drop row
Notes: "bidv-fake.com" literal naming plus brackets.

75.Drop row
Notes: "[phishingSite.com]" literally names itself phishing; unmistakable placeholder.

76.Drop row
Notes: Sequential "0123456789" is the only contact given, an obvious placeholder.

77.Drop row
Notes: Bracket-wrapped "jkl-bank-update.org" URL is a template artifact.

78.Drop row
Notes: Double bracket artifacts ([123456], [techcombank-verify.com]) read as unresolved template syntax.

79.Drop row
Notes: Sequential "0123456789" is the only contact given, an obvious placeholder.

80.Drop row
Notes: Bracket-wrapped "[vietpay-update.com]" is a template artifact.

81.Drop row
Notes: Sequential "0123456789" account number plus an implausible 2.3-billion-VND ask.

82.Relabel to: bank_impersonation
Notes: Fake Paychex rep pressures immediate Smart OTP entry under lock threat.

83.Relabel to: bank_impersonation
Notes: Fake ZaloPay support phone-verification pretext, impersonation not task.

84.Drop row
Notes: Bracket-wrapped "[https://securebanking.com/verify]" is a template artifact.

85.Drop row
Notes: Bracket-wrapped "[http://verifyaccount.vn]" is a template artifact.

86.Relabel to: bank_impersonation
Notes: Fake BIDV "account manager" urges an urgent password change, impersonation not task.

87.Relabel to: bank_impersonation
Notes: Fake Shopee support requests an OTP over the phone tied to a bogus order issue.

88.Relabel to: bank_impersonation
Notes: Fake Momo verification link over a bogus fraud alert.

89.Relabel to: bank_impersonation
Notes: Fake MBBank rep pressures an urgent password change by phone.

90.Drop row
Notes: Bracket-wrapped "[vpbank-secure-login.com]" is a template artifact.

91.Relabel to: bank_impersonation
Notes: Generic bank-security pretext asking victim to send an OTP to a phone number.

92.Drop row
Notes: Bracket-wrapped "[mbbank-verify.com]" is a template artifact despite the phone contact also present.

93.Relabel to: benign
Notes: Standard-style OTP transaction notice telling the user to enter the code in their own app, with genuine anti-fraud advice ("contact us if this wasn't you"); no threat, no link, no request to reveal the code.

94.Drop row
Notes: Bracket-wrapped "[http://verify-account.vn]" is a template artifact despite the police-impersonation framing.

95.Drop row
Notes: Bracket-wrapped leetspeak "[https://amaz0n-login.com]" is an unmistakable placeholder.

96.Drop row
Notes: Bracket-wrapped "[fake-link]" cash-giveaway lure is an explicit placeholder.

97.Drop row
Notes: Bracket-wrapped "[fakeURL.net]" investment-scam link is an explicit placeholder.

98.Drop row
Notes: Bracket-wrapped "[bidv-authenticate.com]" is a template artifact.

99.Drop row
Notes: Bracket-wrapped "[http://secure-bank.vn]" is a template artifact.

100.Drop row
Notes: Bracket-wrapped "[techcombank-update.com]" is a template artifact.

101.Drop row
Notes: Bracket-wrapped "[http://trungthuong10trieu.com]" prize-claim URL is a template artifact.

102.Relabel to: bank_impersonation
Notes: Fake Vietcombank hotline-verification call over a bogus suspicious transaction.

103.Drop
Note: terrible scam message

104.Drop row
Notes: Bracket-wrapped OTP code and domain ([654321], [vcb-smartotp.com]) are template artifacts.

105.Relabel to: bank_impersonation
Notes: Generic "account under attack" pretext directly soliciting an OTP by phone; institutional phishing not task.

106.Drop row
Notes: Bracket-wrapped "[vpbank-secure.com]" is a template artifact.

107.Relabel to: benign
Notes: Plain accountant-role recruitment ad with no fee request, urgency, or suspicious link; reads as an ordinary job posting, not a scam.

108.Relabel to: bank_impersonation
Notes: Fake Techcombank hack alert pressuring an immediate password change under an account-lock threat.

109.Drop row
Notes: Bracket-wrapped "[link]" placeholder is a template artifact.

110.Drop row
Notes: Bracket-wrapped "[link]" placeholder is a template artifact.

111.Drop row
Notes: Bracket-wrapped "[link]" placeholder is a template artifact.

112.Drop row
Notes: Bracket-wrapped "[link]" placeholder is a template artifact.

113.Drop row
Notes: Bracket-wrapped "[link]" placeholder is a template artifact.

114.Relabel to: bank_impersonation
Notes: Fake Agribank "you won a prize" lure driving OTP entry; the unsolicited-prize hook is the manipulation, not a benign notice.

115.Relabel to: zalo_social_engineering
Notes: Classic lost-phone/borrowed-device plea impersonating a friend, directing an urgent bank transfer; not a task lure.

116.Relabel to: zalo_social_engineering
Notes: "New number" friend-in-a-hurry plea for a direct transfer; "no OTP needed" is a pressure cue, not a task.

117.Relabel to: zalo_social_engineering
Notes: Hacked-Zalo-account impersonation with a hospital-fee emergency driving a Momo transfer.

118.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook "secondary account" impersonation of a classmate asking for urgent tuition money.

119.Relabel to: zalo_social_engineering
Notes: "New number, lost phone" friend impersonation requesting an urgent transfer for hospital fees.

120.Relabel to: zalo_social_engineering
Notes: "New number" friend impersonation asking for urgent rent money.

121.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook-and-lost-SIM impersonation of a friend stranded on a business trip, urgent transfer request.

122.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation with a tuition-deadline threat driving an urgent bank transfer.

123.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting a direct transfer.

124.Relabel to: zalo_social_engineering
Notes: Hacked-Zalo impersonation claiming a company payment emergency to solicit a transfer.

125.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation with a strained "buy Netflix for my brother's online class" pretext for a MoMo transfer.

126.Relabel to: zalo_social_engineering
Notes: "New Zalo account" impersonation asking a contact to front a payment, with a slightly contradictory refund promise.

127.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting urgent hospital-fee money.

128.Relabel to: zalo_social_engineering
Notes: "New number" friend impersonation asking the victim to buy and photograph a phone-credit card code.

129.Relabel to: zalo_social_engineering
Notes: Relative impersonation citing a hospital emergency to request an urgent transfer.

130.Relabel to: zalo_social_engineering
Notes: Friend impersonation claiming a card lockout to solicit a "temporary" transfer.

131.Relabel to: zalo_social_engineering
Notes: Hacked-Zalo impersonation with a same-day tuition deadline soliciting a Momo transfer.

132.Relabel to: zalo_social_engineering
Notes: "Friend stranded abroad" impersonation with a fabricated hospital-fee emergency and even an offer of "documents" as proof.

133.Relabel to: zalo_social_engineering
Notes: Hacked-account impersonation claiming to be stranded abroad, needing a hotel-deposit transfer.

134.Relabel to: zalo_social_engineering
Notes: "Lost phone, new account" friend impersonation requesting urgent hospital-fee money.

135.Relabel to: zalo_social_engineering
Notes: "Lost phone" friend impersonation requesting a direct transfer.

136.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook "neighbor" impersonation citing a hospital-fee emergency for a bank transfer.

137.Relabel to: zalo_social_engineering
Notes: Fake HR/director impersonation pressuring an employee to front a "payroll" payment; workplace-trust exploit, not a bank or task scam.

138.Relabel to: zalo_social_engineering
Notes: Hacked-Zalo "secondary account" impersonation with a same-day tuition deadline.

139.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting a direct transfer.

140.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation with an exaggerated "no surgery without payment" hospital threat; still a personal-relationship money ask, not a task.

141.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook classmate impersonation with an exaggerated expulsion threat over unpaid tuition.

142.Relabel to: zalo_social_engineering
Notes: Borrowed-phone friend impersonation requesting a small "urgent phone credit" transfer.

143.Relabel to: zalo_social_engineering
Notes: Old-classmate impersonation over a strained "deposit forfeiture" pretext requesting a transfer.

144.Relabel to: zalo_social_engineering
Notes: "Abroad, can't call" friend impersonation requesting a hotel-deposit transfer.

145.Relabel to: zalo_social_engineering
Notes: Neighbor's-daughter impersonation claiming a locked account abroad to request rent money.

146.Relabel to: zalo_social_engineering
Notes: "New number, broken phone" friend impersonation requesting a small repair-fee transfer.

147.Relabel to: zalo_social_engineering
Notes: Neighbor's-son relay impersonation requesting an urgent business-payment transfer.

148.Relabel to: zalo_social_engineering
Notes: Locked-app impersonation with a strained "can't withdraw from Momo" excuse requesting a tuition transfer.

149.Relabel to: zalo_social_engineering
Notes: "Mother borrowing a neighbor's phone" impersonation citing a hospital emergency to request money.

150.Relabel to: zalo_social_engineering
Notes: Fake go-between impersonation relaying a friend's hospital-fee request.

151.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook "secondary Zalo" impersonation with an exaggerated expulsion threat over tuition.

152.Relabel to: zalo_social_engineering
Notes: "Borrowed phone" child impersonation requesting urgent supplemental-tuition money.

153.Relabel to: zalo_social_engineering
Notes: "Abroad, secondary Messenger account" friend impersonation with an inflated repayment promise ("pay back extra").

154.Relabel to: zalo_social_engineering
Notes: "Stranded at the airport" friend impersonation with a nonsensical "I'll send the OTP after you transfer" line; still a direct-transfer social-engineering ask.

155.Relabel to: zalo_social_engineering
Notes: "Pickpocketed at the airport" friend impersonation requesting urgent flight-ticket money.

156.Relabel to: zalo_social_engineering
Notes: Friend impersonation asking the victim to buy and photograph a game gift-card code.

157.Relabel to: zalo_social_engineering
Notes: "Changed number" friend impersonation requesting a direct transfer for a game top-up, explicitly waving off OTP.

158.Relabel to: zalo_social_engineering
Notes: "Lost phone, new account" friend impersonation requesting a direct transfer.

159.Relabel to: zalo_social_engineering
Notes: "Forgot my phone" colleague impersonation requesting urgent phone-credit money.

160.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting an urgent transfer.

161.Relabel to: zalo_social_engineering
Notes: Zalo-on-desktop pretext impersonating a friend for an urgent tuition transfer, with a strained "refund via Smart OTP" line.

162.Relabel to: zalo_social_engineering
Notes: "New number" friend impersonation citing a hospital emergency and a card-eating ATM to request money.

163.Relabel to: zalo_social_engineering
Notes: "Lost phone, borrowed device" friend impersonation requesting urgent tuition money.

164.Relabel to: zalo_social_engineering
Notes: "New SIM" friend impersonation citing a hospital transfer emergency and a card-eating ATM.

165.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation claiming to be stranded abroad, requesting a hotel-deposit transfer.

166.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation with a same-day tuition deadline.

167.Relabel to: zalo_social_engineering
Notes: Hacked-Zalo impersonation requesting a Momo transfer for tuition.

168.Relabel to: zalo_social_engineering
Notes: "Borrowed a friend's Zalo" impersonation requesting a small urgent tuition transfer.

169.Relabel to: zalo_social_engineering
Notes: Former-coworker impersonation with a "don't call, roaming is expensive" excuse requesting urgent travel money.

170.Relabel to: zalo_social_engineering
Notes: Hacked-account impersonation with a same-day tuition deadline requesting a transfer.

171.Relabel to: zalo_social_engineering
Notes: "New number" father impersonation citing a Smart OTP glitch to request a large business-partner transfer.

172.Relabel to: zalo_social_engineering
Notes: "Abroad, out of roaming credit" friend impersonation requesting a direct loan transfer.

173.Relabel to: zalo_social_engineering
Notes: "Reported/banned Facebook" impersonation with a strained "client's domain renewal fee" pretext requesting a transfer.

174.Relabel to: zalo_social_engineering
Notes: "Mistaken transfer, please send it back" pretext is a direct social-engineering money ask, not a task.

175.Relabel to: zalo_social_engineering
Notes: "Mistaken transfer" pretext paired with a fake bank-branded refund link; still personal-message social engineering, not a task.

176.Relabel to: zalo_social_engineering
Notes: Hacked-Zalo "sister" impersonation citing a hospital-fee emergency.

177.Relabel to: zalo_social_engineering
Notes: "Abroad, new SIM" child impersonation requesting an urgent MoMo transfer.

178.Relabel to: zalo_social_engineering
Notes: "Stranded abroad, card locked" friend impersonation requesting an urgent transfer.

179.Relabel to: zalo_social_engineering
Notes: "Broken phone, temporary number" friend impersonation requesting an urgent hospital-fee transfer.

180.Relabel to: zalo_social_engineering
Notes: "New number, blocked Visa card" friend impersonation requesting an urgent transfer.

181.Relabel to: zalo_social_engineering
Notes: "Stranded at the airport, card locked" friend impersonation paired with a currency-exchange link; still a personal-relationship money ask.

182.Relabel to: zalo_social_engineering
Notes: "New number, locked SIM" colleague impersonation with a fabricated KYC-freeze pretext requesting a business-payment transfer.

183.Relabel to: zalo_social_engineering
Notes: "Borrowed phone, abroad" friend impersonation asking the victim to buy and send phone-credit codes.

184.Relabel to: zalo_social_engineering
Notes: "Borrowed phone" friend impersonation requesting urgent COD-shipping money, with a strained "OTP banking" refund line.

185.Relabel to: zalo_social_engineering
Notes: "Lost phone, colleague relaying" friend impersonation requesting a small urgent transfer.

186.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting urgent hospital-fee money.

187.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting a deposit for new housing.

188.Relabel to: zalo_social_engineering
Notes: Old-classmate impersonation with an odd "2.5k means 2.5 million" clarification and a vague "couldn't receive OTP" excuse; still a direct-transfer social-engineering ask.

189.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation citing a same-day rental-deposit deadline.

190.Relabel to: zalo_social_engineering
Notes: "Lost phone, new account" friend impersonation requesting a direct transfer.

191.Relabel to: zalo_social_engineering
Notes: "Abroad, lost phone and wallet" friend impersonation requesting an urgent transfer.

192.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation requesting a MoMo top-up for a plane ticket home.

193.Relabel to: zalo_social_engineering
Notes: "Lost phone, bank account locked" friend impersonation requesting an urgent transfer.

194.Relabel to: zalo_social_engineering
Notes: "Hospital, dead phone battery" child impersonation with an exaggerated discharge threat requesting urgent hospital-fee money.

195.Relabel to: zalo_social_engineering
Notes: "New Zalo account" impersonation with a strained "forgot to link my card" pretext requesting a transfer.

196.Relabel to: zalo_social_engineering
Notes: "Stranded, pickpocketed" colleague impersonation using a nonsensical "hotel's Smart OTP to text you" claim; still a direct-transfer social-engineering ask.

197.Relabel to: zalo_social_engineering
Notes: "Hospital, phone dying" friend impersonation requesting an urgent surgery-deposit transfer.

198.Relabel to: zalo_social_engineering
Notes: "Lost phone, borrowed device" friend impersonation requesting a direct transfer.

199.Relabel to: zalo_social_engineering
Notes: "Lost phone" friend impersonation requesting urgent tuition money.

200.Relabel to: zalo_social_engineering
Notes: Hacked-Zalo impersonation with an implausible "buy me an Agribank e-card and photograph it" request; still a personal-relationship money ask.

201.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook "secondary account" impersonation requesting an urgent Momo transfer.

202.Relabel to: zalo_social_engineering
Notes: "Deleted the banking app by mistake" impersonation requesting a stand-in transfer for a business partner.

203.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting a direct transfer.

204.Relabel to: zalo_social_engineering
Notes: "Abroad, account locked" impersonation with an exaggerated expulsion threat over tuition.

205.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation requesting a small MoMo transfer for tuition.

206.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation with a same-day noon deadline for tuition money.

207.Relabel to: zalo_social_engineering
Notes: "New number, lost phone" friend impersonation requesting hospital-fee money.

208.Relabel to: zalo_social_engineering
Notes: "Lost phone, borrowed device" friend impersonation requesting a direct transfer.

209.Relabel to: zalo_social_engineering
Notes: "Abroad, locked account" friend impersonation requesting a stand-in transfer.

210.Relabel to: zalo_social_engineering
Notes: Fake go-between "little sister" impersonation relaying a deposit request.

211.Relabel to: zalo_social_engineering
Notes: "Broken phone, borrowed number" friend impersonation requesting a direct transfer.

212.Relabel to: zalo_social_engineering
Notes: "New account, lost phone" friend impersonation requesting hospital-fee money.

213.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook "new Zalo" impersonation with a same-day tuition deadline.

214.Relabel to: zalo_social_engineering
Notes: "Locked banking app" impersonation requesting a stand-in transfer, explicitly asking not to message the old account.

215.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook "new Zalo" impersonation with a fabricated shop-payment emergency.

216.Relabel to: zalo_social_engineering
Notes: "Abroad, OTP unreachable" friend impersonation requesting urgent hotel money.

217.Relabel to: zalo_social_engineering
Notes: Old-classmate impersonation requesting bus-fare money, with an out-of-place "Venmo" repayment promise.

218.Relabel to: zalo_social_engineering
Notes: "New account, lost phone" friend impersonation requesting a direct transfer.

219.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting hospital-fee money.

220.Relabel to: zalo_social_engineering
Notes: "New account" impersonation explicitly discouraging questions while requesting a transfer.

221.Relabel to: zalo_social_engineering
Notes: "Abroad, locked account" impersonation waving off OTP while requesting an urgent transfer.

222.Relabel to: zalo_social_engineering
Notes: "Lost phone, borrowed device" friend impersonation requesting a direct transfer.

223.Relabel to: zalo_social_engineering
Notes: "New account, lost phone" friend impersonation requesting hospital-fee money.

224.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook old-classmate impersonation requesting a same-day tuition transfer.

225.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting a direct transfer.

226.Relabel to: zalo_social_engineering
Notes: "Changed number, abroad" friend impersonation requesting a large business-partner transfer.

227.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook "secondary account" impersonation requesting a friend-of-a-friend transfer.

228.Relabel to: zalo_social_engineering
Notes: "Pickpocketed on a business trip" friend impersonation requesting urgent bus-fare money.

229.Relabel to: zalo_social_engineering
Notes: Neighbor's-daughter impersonation citing a hospital emergency, stacking several financial mishaps at once.

230.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook "new nick" impersonation requesting a card-decline stand-in payment.

231.Relabel to: zalo_social_engineering
Notes: "Lost phone, borrowed device" friend impersonation requesting a rental-deposit transfer.

232.Relabel to: zalo_social_engineering
Notes: "Mistaken transfer" pretext layered onto a hacked-Zalo "old classmate" impersonation.

233.Relabel to: zalo_social_engineering
Notes: Hacked-Zalo impersonation citing a changed phone number to explain a login failure, requesting a tuition transfer.

234.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook classmate impersonation with an exaggerated expulsion threat over tuition.

235.Relabel to: zalo_social_engineering
Notes: "New account, lost phone" friend impersonation requesting a direct transfer.

236.Relabel to: zalo_social_engineering
Notes: Fake "my Zalo was hacked, don't trust it" warning that pivots into its own hospital-fee money request.

237.Relabel to: zalo_social_engineering
Notes: "New number, lost phone" friend impersonation requesting a direct transfer.

238.Relabel to: zalo_social_engineering
Notes: "Lost phone, locked bank account" friend impersonation requesting hospital-fee money.

239.Relabel to: zalo_social_engineering
Notes: Neighbor's-child impersonation citing a hospital surgery-payment emergency.

240.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook "changed number" impersonation requesting a stand-in contract payment.

241.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation with a same-day tuition deadline.

242.Relabel to: zalo_social_engineering
Notes: Hacked-Zalo impersonation citing a 30-minute order deadline to request a Momo transfer.

243.Relabel to: zalo_social_engineering
Notes: "Lost phone, borrowed device" friend impersonation requesting a direct transfer.

244.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting a direct transfer.

245.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation with an exaggerated "mother thrown out of the hospital" threat over unpaid fees.

246.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation where the requested account name doesn't match the sender's claimed name; still a personal-relationship money ask.

247.Relabel to: zalo_social_engineering
Notes: Old-classmate impersonation with a contrived "power shut off at 11:59" deadline for a utility-bill transfer.

248.Relabel to: zalo_social_engineering
Notes: "Abroad, no SIM" friend impersonation waving off OTP while requesting a hotel-deposit transfer.

249.Relabel to: zalo_social_engineering
Notes: "Changed number, abroad" friend impersonation requesting a stand-in payment.

250.Relabel to: zalo_social_engineering
Notes: Neighbor's-child impersonation citing a hospital surgery-payment emergency.

251.Relabel to: bank_impersonation
Notes: Fake internal-IT colleague phishing a Smart OTP through a fraudulent Vietcombank-styled portal link; credential theft via a fake link, not a task.

252.Relabel to: zalo_social_engineering
Notes: Hacked-Zalo impersonation paired with a fake Shopee-styled order link to request a Momo stand-in payment.

253.Relabel to: zalo_social_engineering
Notes: "Close friend" impersonation asking to borrow the victim's bank account to fabricate a loan statement; trust-based account-mule recruitment, not a task.

254.Relabel to: zalo_social_engineering
Notes: "Phone dropped in water" child impersonation requesting a rental-deposit transfer.

255.Relabel to: zalo_social_engineering
Notes: Friend impersonation citing a child's medical emergency to request urgent hospital money.

256.Relabel to: zalo_social_engineering
Notes: "Father, borrowed phone" impersonation requesting a surgery-deposit transfer, despite claiming to be fine.

257.Relabel to: zalo_social_engineering
Notes: "Sister, borrowed phone" impersonation citing a mother's emergency surgery to request money.

258.Relabel to: zalo_social_engineering
Notes: Old-acquaintance impersonation requesting a stand-in online-order payment under a 15-minute deadline.

259.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting tuition money.

260.Relabel to: zalo_social_engineering
Notes: "New number" friend impersonation requesting a stand-in online-order payment.

261.Relabel to: zalo_social_engineering
Notes: "Lost phone, borrowed device" friend impersonation requesting rent money.

262.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook "new Zalo number" impersonation requesting a stand-in order payment under a same-day deadline.

263.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook "secondary account" impersonation requesting a stand-in transfer for a work deadline.

264.Relabel to: zalo_social_engineering
Notes: Neighbor's-daughter impersonation citing a sudden hospitalization to request money.

265.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting a direct transfer.

266.Relabel to: zalo_social_engineering
Notes: Hacked-account "new Zalo" impersonation citing a 30-minute order deadline to request a transfer.

267.Relabel to: zalo_social_engineering
Notes: "Abroad, slow roaming data" colleague impersonation requesting a hotel-deposit transfer.

268.Relabel to: zalo_social_engineering
Notes: "Lost phone, borrowed device" friend impersonation requesting hospital-fee money.

269.Relabel to: zalo_social_engineering
Notes: "New account, lost phone" friend impersonation requesting a direct transfer.

270.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation requesting a Momo or bank transfer.

271.Relabel to: zalo_social_engineering
Notes: "Locked Facebook, abroad" friend impersonation waving off OTP while requesting a hotel-deposit transfer.

272.Relabel to: zalo_social_engineering
Notes: "New number" friend impersonation paired with a fake bank-styled payment link to request a rental-deposit transfer.

273.Relabel to: zalo_social_engineering
Notes: "Abroad, OTP unreachable" friend impersonation promising a Western Union repayment while requesting an urgent transfer.

274.Relabel to: zalo_social_engineering
Notes: "New number" colleague impersonation citing a boss's payment request to solicit a stand-in transfer.

275.Relabel to: zalo_social_engineering
Notes: "Abroad, locked e-wallet" friend impersonation requesting a plane-ticket transfer.

276.Relabel to: zalo_social_engineering
Notes: "Borrowed a nurse's phone" friend impersonation citing a hospital surgery-payment deadline.

277.Relabel to: zalo_social_engineering
Notes: "Lost phone, new number" friend impersonation requesting hospital-fee money.

278.Relabel to: zalo_social_engineering
Notes: Hacked-Zalo "sister" impersonation citing a mother's surgery to request money.

279.Relabel to: zalo_social_engineering
Notes: "Abroad, blocked credit card" impersonation requesting a hotel-deposit transfer, with a promised "bonus" for helping.

280.Relabel to: zalo_social_engineering
Notes: "Best friend" impersonation with a hacked-Facebook pretext requesting a same-day tuition transfer.

281.Relabel to: zalo_social_engineering
Notes: "New number, broken phone" friend impersonation requesting a rental-deposit transfer.

282.Relabel to: zalo_social_engineering
Notes: "Card eaten by the ATM" friend impersonation requesting a stand-in online payment.

283.Relabel to: zalo_social_engineering
Notes: "Abroad, locked account" friend impersonation requesting a stand-in payment for a business partner.

284.Relabel to: zalo_social_engineering
Notes: "Mother, borrowed phone" impersonation requesting money for phone repair and medicine.

285.Relabel to: zalo_social_engineering
Notes: "Abroad, locked VCB account" friend impersonation requesting a plane-ticket transfer.

286.Relabel to: zalo_social_engineering
Notes: Mother impersonation using a relative's Zalo account to request hospital-fee money.

287.Relabel to: zalo_social_engineering
Notes: Hacked-Facebook impersonation asking the victim to buy and send phone-credit codes for a game top-up.

288.Relabel to: zalo_social_engineering
Notes: "Mistaken transfer, please send it back" pretext is a direct social-engineering money ask, not a task.

289.Relabel to: zalo_social_engineering
Notes: "Abroad, no SIM" friend impersonation requesting urgent airport money.

290.Relabel to: zalo_social_engineering
Notes: "Borrowed a friend's Zalo" impersonation requesting a stand-in deposit payment.

291.Relabel to: zalo_social_engineering
Notes: "Lost phone, borrowed device" friend impersonation requesting a direct transfer.

292.Drop row
Notes: Bracket-wrapped "[fakeurl.com]" is a template artifact.

293.Drop row
Notes: Bracket-wrapped "[http://cafc-support.vn]" is a template artifact.

294.Drop row
Notes: Bracket-wrapped "[fakeurl.com]" is a template artifact.

295.Relabel to: bank_impersonation
Notes: Fake Smart OTP security-alert callback lure, impersonation phishing not task.

296.Drop row
Notes: Bracket-wrapped "[https://cafc-vn.com]" is a template artifact.

297.Relabel to: benign
Notes: Routine transaction-confirmation OTP notice with a standard "didn't request this? call us" safety line; no threat, no link, no request to reveal the code.

298.Drop row
Notes: Bracket-wrapped "[linkscam.vn]" literally names itself a scam link; unmistakable placeholder.

299.Drop row
Notes: Bracket-wrapped "[https://cafc-help.vn]" is a template artifact.

300.Drop row
Notes: Bracket-wrapped "[phishing-site.vn]" literally names itself phishing; unmistakable placeholder.

301.Drop row
Notes: Bracket-wrapped "[taxscam.com]" literally names itself a scam; unmistakable placeholder.

302.Relabel to: bank_impersonation
Notes: Fake fraud-recovery "investigator" phishing an OTP by phone; recovery-scam impersonation, not task.

303.Relabel to: bank_impersonation
Notes: Fake Vietcombank rep directly requests ID and Internet Banking password by phone.

304.Drop row
Notes: Bracket-wrapped "[verifyaccount.vn]" is a template artifact.

305.Drop row
Notes: Bracket-wrapped "[fakeurl.com]" is a template artifact.

306.Drop row
Notes: Bracket-wrapped "[activation-link.com]" is a template artifact.

307.Relabel to: bank_impersonation
Notes: Fake fraud-recovery "investigator" phishing a Smart OTP code by phone.

308.Drop row
Notes: Bracket-wrapped "[fakeurl.vn]" is a template artifact.

309.Relabel to: bank_impersonation
Notes: Fake fraud-recovery "investigator" directly requests a username and password by phone.

310.Drop row
Notes: Bracket-wrapped "[link]" placeholder is a template artifact.

311.Drop row
Notes: Bracket-wrapped "[http://techcombank-auth.com]" is a template artifact.

312.Drop row
Notes: "fakebank.com.vn" literal naming plus brackets.

313.Drop row
Notes: Bracket-wrapped "[link]" placeholder is a template artifact.

314.Relabel to: bank_impersonation
Notes: Fake Vietcombank support urging an immediate callback over a vague account issue.

315.Relabel to: benign
Notes: Routine payment-confirmation OTP notice with a standard "didn't request this? report it" line; no threat, no link, no request to reveal the code.

316.Drop row
Notes: Bracket-wrapped "[link]" placeholder is a template artifact.

317.Relabel to: benign
Notes: Routine purchase-confirmation OTP notice that explicitly says to just ignore it if unrequested; no threat, no link, no credential ask.

318.Drop row
Notes: Bracket-wrapped "[http://updateaccount.info]" is a template artifact.

319.Drop row
Notes: Bracket-wrapped "[link]" placeholder is a template artifact.

320.Relabel to: Beigin
Note: beigin , only scam if the bank name is different

321.Drop row
Notes: Vague, unnamed "promo program" with sequential "0123456789" hotline is an obvious placeholder.

322.Drop row
Notes: Bracket-wrapped "[link]" placeholder is a template artifact.

323.Drop row
Notes: Bracket-wrapped "[https://agribank-update.com]" is a template artifact.

324.Drop row
Notes: Bracket-wrapped "[http://securelogin.net]" is a template artifact.
