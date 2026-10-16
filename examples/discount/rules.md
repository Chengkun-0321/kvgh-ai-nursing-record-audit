# ③ 業務規則與異常行為

`final_price(amount, is_member)` 計算訂單應付金額。

| 編號 | 規則 |
|---|---|
| R1 | `amount` 大於或等於 1000 時，先打九折（乘以 0.9）。小於 1000 不打折。 |
| R2 | `is_member` 為 True 時，在 R1 之後再減 50 元。 |
| R3 | 結果不得低於 0；低於 0 時回傳 0。 |
| R4 | 結果四捨五入到小數第 2 位。 |
| E1 | `amount` 為負數時，拋出 `ValueError`。 |
| E2 | `amount` 不是 int 或 float（例如字串、None）時，拋出 `TypeError`。bool 也視為不合法。 |
