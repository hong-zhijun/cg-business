import requests


headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=0, i",
    "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
}
cookies = {
    "__Host-next-auth.csrf-token": "262f512d44d0830e7b109143a218c081f3daf0823013a7176b825460ab083677%7C2bee662ef7cfafae5bcf4f0b72c349e1f9594fc57bb1249e1a02398547e33a46",
    "oai-did": "8d181987-e570-4954-b957-88ab5e4655a8",
    "__cf_bm": "5wH8j9UgA3B.fJJQt8fS1KY.LBcfrIJnAl_FVUEj5_A-1767083399-1.0.1.1-SGDM8CqchwJZgDoRQ6WUqccgHOIMm6rfUw79ztZSk0mYY_M5pJMd91FAE2mNVgeNmxYZFVrSz9OqS5W90lvR9jMBF.y3BMR4lvpPnIqu3kU",
    "_cfuvid": "7W3Jdd9bq7GmHEMVcxeqzdt1b1eYgu5BtE5ipbZ2wnY-1767083399366-0.0.1.1-604800000",
    "cf_clearance": "h6oPOdoLAvfApEsDneJMnqpoxNVUiH7OI.PV2ktpbXQ-1767083404-1.2.1.1-InHP9qFjg2c8GVNpQEgEHRQaH2DHRpFmv3R18nnE23s_85NwS7b9JbI8DsaBlwkoUYE9f5riRGs8GQPoqZOD30qm_fQ3ZM6Q2U1sfZC7KMr0wY8SrU8sRF1aqviPKbyD6nMJI0WM6vnAJfVrAM4jRpAx02MSEcA2I03nL7fkhLuLNHDAXb2jHt2RXiw2SOXvEHGcAyvYyyJoDlxgCG9j.IcsKbrSRaNldsBa1KaEYmI",
    "__Secure-next-auth.callback-url": "https%3A%2F%2Fchatgpt.com%2F",
    "oai-hlib": "true",
    "__Secure-next-auth.session-token": "eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..GEP-w8y-xawgAYv2.fn6Rs_MSiCiM0k-5K4NMP38ozntPzuQ2HmeAknYs_zqeyae8ktcwHgsVjC-3Ci8oe3y1f26i_5zKiwBvcwgDocIvDwrEgJyeKcv1u1tA9SleNT-oS5Qd8Yc9AzxaL7oGsbWFfxbSKsbY-cLCc0kRFi1ELNM8HSuiLmCRx7S-LiJdSKFcdhy1qJp0eVnVI4-GVsuLsFkqRIKedvgL--5dt4BcTU-RdowwlDJ6fte_KtrRNPZ7_xRIAXoRB80_jM7nJa1NLhPT6rLXhsGrLZip4SUCmTAYjtepEAHzSFKzpeHXmMBoFuL8NbG1tXoe5HcJLkGoopCSosIPmPTjBv2NrJDYP1NTH3faaPc7AVxk0NqLcTt5LtKf2BEBPAAdNl8tBXgc8zdgVo0KuPDNpexJYIsa83RhklXtowq_0U74-jO04WknjAKmjpyYj2GCMUAIhtwkoTBMGKW5MFuUgPZpItkW1Q17-6toxH3sCQv8Jo2NLN92F7ZjrpdOOUknn4sMbGxaHg0Z6st4ZtjyIV-bivY_HxZFZ_pc0RgaZKKcBr1TIe_zmz9BlFiQQJvkJqL8HTarnM7hCSM6dLoEHBINbWpUJipevikJs07EGOka7fyb9_OUfw84tTUfIoi5ssUjvoTcLoWIk5Jb8JG_l7wqd9Gaz6KxyF1GwgtSnDvv2ghaUD4FQkcUHQWHOruCENszgxWwat2tZBRA7CWQG3TUClO6BO50SNv_1po43w0WnVa19lggPu6z4h5AHdnc-96FvLFHMIuxCXx7GqSVGbVEBy_1gBVEHmGNz91uppMk65neQoEExCqgachzUgM2xBLIYIylNCRxUXZkwwbBgSBwoaoWqCNcIZYxKbhUQ2mGCaPZwREyD8Oqx81W-sF-8TDDzH-ttDfgpramSCFhEmpNZP5JqslNjpXUO-po_YkWWYRms9oYxNSt38qMwCtpBOaznUsf8c0_Oz1MvQfCv-GhTKrSUnat-EVeMQFo_Yo1NXtFPiiPfpUyUMKdqXFw5YOikEReVlDuHTjzdPIAbzXST_8RmvK8j4iWZY5wDatI1RNO8mqUckGf2VkvqImOhjO4geJE4wfpF6D7PHX5o0nN_Qd0bW52otsRJPGPluFxXas0h7SwXUp6AAmmD03RNZqRqy-RCpHVcX8NdpsxqtOLP3P3-GJeOG6mIlshjo4kYkW8Q5VN3E9gA1EuOT8WDo8umc3gq5aFAqsVl2i1-jaS32OMXGD24aWMR-y7mQLK20oj0sLD3y4ORO3i8EkXotia60vKH5XFZnrI2QYC29Aiz3ub_Mc4r11QFS-e-ub649Kjvy3P5CoBfIDWTrYrEGcGz8dxfQbZ7BiGSWRiuAQUo9U2a42FMKjressQOxabYm8Bqt3PDNEqEHaCfVHPNNrcXOPK0ZrIPPyu35i9elIYpbkOczwvXsijlIhJN-8MuIQ_hU_atANLVPQqve_Ns_tgyQ02TMewXk6crU3_ykFuo743uPl5jW9UI8Mxl6KeFc4rHbY2SY3Ud508pz1L-GsleqgNRzq1s7LVVVJ93HgxeRzEgjTA3kUME4mTPoZK091HTCtUpi1hbXdNEfcQeQyh6BdcDYb9ViPIR4P7ATDLlj_cXDYGT-xEi-4SKIQCXEim9TeokwSICowobDUiX0Lv0TTC6-FJ9hRMHYBaHLofWCpWvw7JV0zAJlfuDf9MmOr5ZdiRTm8HoLMs8QmBPNDdLQ5IbtC4ynnKk_c1CSnKkIzkST_oiNB0l7ILFHx82nlURsG-Lfmqu62h4NtjSipog2Yl1FLcJ4Sq-apjgLNwX7uI5WL2GF9no8ulLIeBdAaiswUUYkcaoUmtWLO8xAUF8fQpYmotNE3CbtAzGthaZlXqi9OEPYRYt-YvE0su5RRGih8Gml7oZ2cAKEQl-TI-DtH6ch4bL-PGS6JJP1X_CYU36R7S1BABarTLEuSHG2MMeD9rdqd8Iuj-8Turs3gxazV1BWplUcwf40zenEWxOhmYgOuKAeLL-gE-RJgJjfptOjfvKHR2-jAAzB2APVhokiAsXpUcktsOlyG94Gq8gchZKvPgi3jrzUrfMwIT1UgLOI3s8rB6HxTZ9Q1M25Jigd0oxpsiRBBVtfASdyaj2o9II52ayyhX1OLv7lrYZa40sdsB9WgUJ0j8yABH1lw0kZK09jlKLf7IeqCBjhgSJHChywXaWg7euJ7BHUBgQNFhm9JMLO7yX26WCTpjAxPk_Z3K8oOhRqpMN6CSFTeWiG_RAGjfmmdb4q_fcvysbLj6o0P8kCxlNTYujbNWpc26jfOldjLIYG7juyg4rCIVDmx_nqaVlkExuqEasvRu0JFcug37dGv5ARC681DaEhKnJnGzwsR_Dbl0jThgXoZyLt7x5W7GXNVc7jQTGV6qLPi2Jf5zvshv76t44aNc1Cka_jDmGSZ948t4Wn1fYID_mrsWrdLUSxF7GnAtR688Ek7GCaR-qEZc2C36G09xV9kO_ZPO9uFAT0kvR4nB3AsQXVpgfTkYOX3iLbERV3kin8-26Sjptv9A8WsVkWU9RjQ2ssIUX2KPTu_u_wqXGFN40-1iXEJfiABE7AP1iLzyL8iEQeP2AjpJdqTrrLl0dVV2Gr3nqm9YWHV_aYCHR470T-Go2DbN--LcoesDLhwGY6ywP82p05uWrYJ9hRjDYohTYOJWr9h03kgjPAF476H7CIToeoZTyPunCfqIM0KG6VpbDLjaSDUNUhPLJQUUNgwIsUI8NUeBTiuCnen6vECtZEcRUMvRnYXiQ02HcUdbEjZfNcu6aZX8NNrIh2jmS0YV8InYapEHSQHHLwParrm8r_T6wAcWIxxdHE0Oe7kJSrrKwHkgO0oDSuiiQkErxNro6ernosZ3AczUnNATWZrzHY8V5R-jYsLbxDkhl_GmR7Hb8pHTbJB8MbiRyy72KISNEvlOAKf0nQ4qgEyFAXyOqzb9e0Yx-V79Y77snXvfo5Rq_W91oeOPUiY5hXyC9pyVl2NqKb09f6WUfFQ3bsnHuv6-v7Rzj93C41mtiustRw6Ai8h1eUXRh3mb_RtJvjjO9X0iF8AC_oqPbHlWu9Dl6U86VwT8g0HbcBZfD2MeIfUPfIhUshYSo5axuBMCBhOUqGU.kRN4Z0Li9zKrL8eHFVeBVg",
    "oai-client-auth-info": "%7B%22user%22%3A%7B%22name%22%3A%22hskaw%20ddw%22%2C%22email%22%3A%22pezzjhkyn80%40outlook.com%22%2C%22picture%22%3Anull%2C%22connectionType%22%3A1%2C%22timestamp%22%3A1767083840190%7D%2C%22isOptedOut%22%3Afalse%7D",
    "oai-gn": "",
    "__cflb": "0H28vzvP5FJafnkHxj4E5h8p2cLDRvYbwUtRNqkvYVq",
    "oai-sc": "0gAAAAABpU49PmtlmIDgOk-aPcowvnrf_9kTwEUoNfY0yRHLrSB0eehhGz46lRCh6kTg0OaBcjBHSRmNDoesVNzgLbQ5FKed-TXAVgT5VUUu2yOrxEIc1ffzBCKoMorbnzVWizELgjtEu463C8cfdHvDnLxNaaZGdlw37y9QYEoBoCggIbDwbvcPBN9POZS1uqD1XGdV8ryixbWJqm_cQ54CeEyQUUSoyEWh5T0EVrNYrxJfqKXVy5sk",
    "_uasid": "\"Z0FBQUFBQnBVNDlRRjBzUmJSeVBybUtLN256M1JSa0pEd1FRUzk0M1VZOGNaWVZvalZQTHVjNkVmSmJvaUV3WWNuUklCMUpVb1JLQ1hueU5wLWhPamRTYW4zMnZQS056WjZZTUxQVm9IcUZfV09WdC1tb0cxM0FzSjBEZ3FHMTFrVVdNNDZHeTVCQm02WEpxMUJuUFZXeXpYUlFZTDBFajkxX212dEtFUy11Sk05STgxZ1IxbFZSWXFBWllNdEdOWW5OaS05RTlOSWtmZ0N2NHQyZi1ZWWV1Tko2Qk9sY25XVG9lYzl1QnFOb2RTeEZ6UXRkT0RraFNKU1FBLW92NEg2TFhpVG9SN3BpSk9BaHVZX1N5Nk41THdjQS1pUno2Uk9LQWc2SnBWd19YTjdZUVdiNGNwaDZTTDk1WG9mZG5pSUQ5MUVfLVdvZkNOal85NmtHdzRVMWZKSkk4a1liTXVnPT0=\"",
    "_umsid": "\"Z0FBQUFBQnBVNDlReFpzTW5DU3JHc0dSZFU2M0RUME94dUREZk93VGZpa0M5enpvSm5FUGYzbjNDNjNVXzlDNjhTRGdlZ01vc2lBdjhVUUJKNGFUSlNHUml2eTJmejZKYU4zQkd1OGt2ODlQYWQxNHRKQ0JRQm1GM2V6c2ZMS1puX3FkUVJlUGR0QzRqMEpjYWZBcDBBWlJhM2xVdVM1UWx5cXA3TFlKNno2QUgxUU1JRWg1TER3OGdYNTlmQS1wOXg4UnV6OTNyRFROOVBXOVlCOU1QUFRuYWhId1I4WFVpY3hKbjhQaXdMamE4NHo2Z2Z2RlAybz0=\"",
    "_dd_s": "aid=fef4df46-3580-4576-94e0-d6aca4057dce&rum=0&expire=1767084759847&logs=1&id=7b0ae9f4-5f45-4539-991d-5495f1788596&created=1767083403660",
    "oai-hm": "READY_WHEN_YOU_ARE%20%7C%20WHAT_ARE_YOU_WORKING_ON"
}
url = "https://chatgpt.com/api/auth/session"

def get_session(cookies, proxies=None):
    headers['cookie'] = cookies
    response = requests.get(url, headers=headers, proxies=proxies)

    print(response.text)
    print(response)
    return response.json()