# Khảo sát và đề xuất license Naqex

**Owner đã chấp thuận triển khai ngày 29/10/2026 bằng commit mới, giữ lịch sử
MIT cũ.** Văn bản cấp phép hiện hành nằm trong [LICENSE](../../LICENSE) của mỗi
repo; [hướng dẫn license](../licensing.md) giải thích phạm vi. Nội dung bên dưới
giữ bản đề xuất để đối chiếu quyết định, không phải văn bản cấp phép thứ hai.

Ngày lập: 29/10/2026. Áp dụng dự kiến cho phần do owner sở hữu trong
Workspace, Trader, VI Dubber và Quant Lab. Fork, dependency, vendor, dataset
và notices của bên thứ ba giữ điều khoản riêng.

## Chính sách owner đã chọn

| Tình huống | Quyền dự kiến |
|---|---|
| Xem source, học, nghiên cứu và thử nghiệm phi thương mại | Miễn phí |
| Sửa code chỉ dùng riêng | Miễn phí; không phải công khai bản sửa |
| Cá nhân giao dịch tài khoản của chính họ | Miễn phí, kể cả có lợi nhuận |
| Cá nhân thi hoặc giao dịch tài khoản prop firm được giao cho chính họ | Miễn phí, kể cả nhận payout |
| Chia sẻ bản gốc hoặc bản sửa phi thương mại | Giữ notices/license; công khai source đúng phiên bản |
| Cho người ngoài dùng bản triển khai qua mạng, dù miễn phí | Công khai source ứng dụng đúng phiên bản |
| Bán app, bán quyền truy cập, SaaS thu phí, cung cấp dịch vụ hoặc quản lý tài khoản cho khách | Cần giấy phép thương mại riêng bằng văn bản |
| Naqex tự khai thác phần code có đủ quyền sở hữu | Owner giữ quyền cấp phép và thương mại hóa |

Mã source được chia sẻ không bao gồm mật khẩu, account token, dữ liệu tài
khoản/giao dịch hoặc chiến lược độc lập của người dùng. Nếu sửa trực tiếp source
ứng dụng rồi chia sẻ/host cho người ngoài, phần source ứng dụng đã sửa vẫn
thuộc nghĩa vụ cung cấp source.

Org membership là quyền truy cập GitHub, không tự chuyển quyền tác giả hay cấp
quyền thương mại. Contributor trong org vẫn cần thỏa thuận quyền đối với đóng
góp của họ nếu owner muốn tự cấp phép thương mại cho phần đóng góp đó.

## Proposed license text

The text below is a proposal only. It grants no new rights unless the copyright
holder expressly adopts it for an identified version of the Work. It does not
replace any currently effective repository license.

### Naqex Source Available License 1.0.0 — DRAFT

#### 1. Definitions and scope

"Licensor" means the copyright holder or holders identified in the copyright
notice accompanying the Work, acting under the Naqex name where applicable.
"You" means the person or entity exercising permissions under this License.
"Work" means the application source, scripts and documentation expressly
offered under this License, including modifications to that material.

"Your organization" means the legal entity You act for and its personnel
authorized to work on its behalf, including employees and contractors bound
to confidentiality and use restrictions. A customer, public user or unrelated
person is not internal personnel merely because they join a GitHub organization
or receive repository access. Internal distribution means providing copies
solely to such authorized personnel for use within that organization.

Independent programs that merely use documented interfaces, user data,
credentials, and independently authored strategy files or plug-ins are not part
of the Work solely because they are used with it. Code derived from the Work
remains within its scope regardless of its file name or packaging.

Separately licensed third-party components are governed by their own terms.
This License neither replaces those terms nor grants rights in third-party
software, datasets, models or services. It does not authorize use of trademarks
or imply endorsement by the Licensor.

#### 2. Permitted purposes

Subject to the conditions below, the Licensor grants You a worldwide,
non-exclusive, royalty-free copyright license to use, reproduce, study, modify
and distribute the Work for personal, educational, experimental or research
purposes that do not have a commercial objective.

The following personal trading use is also expressly permitted, even where it
earns a profit: a natural person using the Work exclusively for that person's
own trading, investment decisions or trading records, including accounts held
by that person and evaluation or funded accounts allocated to that person
under their own prop-firm participation. That person's trading gains and
prop-firm payouts do not, by themselves, require a commercial license.

This exception does not permit selling software or services, operating the Work
for customers, managing client accounts, offering paid signals or copy trading,
or using another person's personal-trading permission to operate a business.

#### 3. Commercial permission

Any commercial use outside the personal-trading exception requires a separate
written license from the Licensor before that use begins. This includes sale,
paid licensing or access, commercial hosting, services for clients, and use of
the Work to operate or support a business for commercial advantage. A hosted
service supported by advertising, sponsorship or paid bundles is commercial
even if individual users do not pay for access.

Publishing source does not, by itself, authorize commercial use. A separate
written agreement may grant commercial rights and replace conditions expressly
identified in that agreement, including use, redistribution, downstream
licensing and source disclosure conditions. All other applicable conditions
remain in force. An agreement cannot waive rights held by a third party.

The Licensor retains the right to use and commercially license material for
which it holds the necessary rights. This does not give the Licensor ownership
of someone else's contributions or override a third-party license.

#### 4. Notices and redistribution

Each copy or distribution of the Work must preserve this License and applicable
copyright and third-party notices. Identify material modifications and their
authors or maintainers without implying that the Licensor endorses them.

You may distribute modified versions for permitted purposes only if recipients
receive the same permissions and conditions for the Work and Your modifications
to it. You must have the necessary rights to provide those permissions. Do not
impose additional restrictions that prevent recipients exercising them.

#### 5. Source disclosure

If You distribute the Work outside Your organization, including a modified
version or executable, make
the Complete Source for that exact version publicly available without charge
at the same time, under this License. Include an accessible source link with
the distribution. Source must remain available for at least three years after
Your last distribution of that version; if the source is hosted elsewhere,
ensure it remains available for that period.

If You operate the Work, including a modified version, as a service for people
outside Your own organization, make the Complete Source of the version they
interact with publicly available without charge under this License. Display a
prominent source link accessible to those users while the service operates and
keep that source available for at least three years after that version was last
served. This condition applies to free services as well as commercial services
unless a separate written commercial license expressly provides otherwise.

"Complete Source" means the preferred editable form of the Work and Your
modifications, with the build and installation scripts, dependency version
information and configuration templates needed to reproduce that version.
Publicly available third-party dependencies may be identified by version and
source location instead of being redistributed where their licenses permit.
Separately licensed vendor software must be identified with lawful acquisition
instructions; this License does not authorize redistributing that vendor.

Do not include credentials, private account records, user datasets or unrelated
independent software. Removing secrets must not be used to omit application
code covered by this section; provide safe configuration templates instead.

Private use, internal distribution and modifications that are neither
distributed nor provided to people outside Your organization do not trigger
source disclosure. Commercial
use restrictions still apply, including to internal business use.

#### 6. Existing rights and contributions

This License applies only to versions expressly offered under it. It does not
withdraw permissions already granted for earlier versions under MIT or another
license. Material available under a separate license remains available under
that license according to its terms.

Contributing code does not automatically assign copyright or authorize the
Licensor to relicense a contributor's work commercially. Such rights require an
appropriate separate agreement with that contributor.

#### 7. Compliance and termination

Permissions under this License terminate if You breach its conditions. For a
first breach, permissions are reinstated if You stop the violation, remedy its
effects where reasonably possible, and fully comply within 30 days after
receiving written notice. Any later breach requires the Licensor's written
reinstatement. Termination does not require deletion of records that must be
retained by law and does not cancel independently held third-party rights.

#### 8. Warranty and liability

To the extent permitted by applicable law, the Work is provided as is, without
warranties, including merchantability, fitness for a particular purpose and
non-infringement. The Licensor is not liable for losses arising from its use,
including trading losses, lost profits or lost data, except where applicable
law does not permit that exclusion. You remain responsible for Your decisions
and compliance with broker, market and other applicable rules.

#### 9. Reserved rights

All rights not expressly granted are reserved. Nothing in this License limits
rights that cannot be excluded by applicable law or permissions necessarily
granted to a hosting platform under its terms for displaying and forking a
public repository. For additional permission, contact the Licensor through the
official Naqex repository identified with the Work; a request is not itself a
grant of permission.

## Quyết định triển khai sau khi duyệt

- Đổi license là commit mới; giữ lịch sử Git. Nếu owner có đủ quyền, có thể cấp
  phiên bản hiện tại theo điều khoản mới, kể cả với phần code do mình sở hữu đã
  từng phát hành. Việc đó không hủy quyền MIT của bản đã phát hành: người khác
  có thể tiếp tục dùng, sửa và phân phối bản MIT cũ theo MIT. Điều khoản mới
  không tự áp dụng hồi tố và cũng không tự cấp quyền lấy phần bổ sung mới từ
  bản mới rồi coi phần bổ sung đó là MIT.
- Chỉ thay LICENSE, README, metadata và CI contract của bốn repo tự phát triển;
  không đổi license của fork/dependency. Dùng `LicenseRef-Naqex-Source-Available-1.0.0`
  ở nơi hỗ trợ custom SPDX expression; nơi không hỗ trợ phải dùng khai báo file
  license theo schema của công cụ, không tiếp tục khai là MIT.
- Ghi rõ version/commit bắt đầu áp dụng. Không viết lại lịch sử MIT.
- Nếu là license riêng, GitHub có thể hiển thị "Other" hoặc không tự nhận diện;
  branch protection/CI của repo public không phụ thuộc việc nhận diện license.
- Mốc lưu source ba năm và điều khoản sửa vi phạm 30 ngày là đề xuất thực thi
  của bản dự thảo, không phải câu trả lời đã có trong khảo sát của owner.
- Đây là bản dự thảo chính sách và điều khoản, chưa phải kết luận về khả năng
  thực thi ở một hệ thống pháp luật cụ thể. Cần review pháp lý trước khi dùng
  làm căn cứ cấp phép thương mại hoặc xử lý tranh chấp.

## Nguồn đã đối chiếu

- [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0):
  không có nghĩa vụ cung cấp source; không diễn giải điều khoản personal use
  của bản gốc thành ngoại lệ giao dịch kiếm lời.
- [Open Source Definition](https://opensource.org/osd): giới hạn mục đích thương
  mại không phù hợp định nghĩa open source; gọi chính sách này là source-available.
- [GitHub: licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository):
  public có quyền xem/fork theo terms; dùng license tùy chỉnh có thể không được
  bộ nhận diện của GitHub nhận ra.
- [Open Source Guides: changing a license](https://opensource.guide/legal/#what-if-i-want-to-change-the-license-of-my-project):
  phân biệt đổi license cho release mới với quyền đối với đóng góp/code cũ.
