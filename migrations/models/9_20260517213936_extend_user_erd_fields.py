from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "privacy_agreed_at" TIMESTAMPTZ;
        ALTER TABLE "users" ADD "ban_reason" TEXT;
        ALTER TABLE "users" ADD "nickname" VARCHAR(10) UNIQUE;
        ALTER TABLE "users" ADD "withdrawal_reason" TEXT;
        ALTER TABLE "users" ADD "refresh_token_hash" VARCHAR(255);
        ALTER TABLE "users" ADD "social_provider" VARCHAR(20);
        ALTER TABLE "users" ADD "social_id" VARCHAR(128);
        ALTER TABLE "users" ADD "password_changed_at" TIMESTAMPTZ;
        ALTER TABLE "users" ADD "deleted_at" TIMESTAMPTZ;
        ALTER TABLE "users" ADD "login_fail_count" INT NOT NULL DEFAULT 0;
        ALTER TABLE "users" ADD "is_banned" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "users" ADD "terms_agreed_at" TIMESTAMPTZ;
        ALTER TABLE "users" ADD "banned_by" BIGINT;
        ALTER TABLE "users" ADD "is_deleted" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "users" ADD "banned_at" TIMESTAMPTZ;
        ALTER TABLE "users" ADD "device_id" VARCHAR(128);
        ALTER TABLE "users" ALTER COLUMN "gender" TYPE VARCHAR(10) USING "gender"::VARCHAR(10);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_users_nicknam_b32a63";
        ALTER TABLE "users" DROP COLUMN "privacy_agreed_at";
        ALTER TABLE "users" DROP COLUMN "ban_reason";
        ALTER TABLE "users" DROP COLUMN "nickname";
        ALTER TABLE "users" DROP COLUMN "withdrawal_reason";
        ALTER TABLE "users" DROP COLUMN "refresh_token_hash";
        ALTER TABLE "users" DROP COLUMN "social_provider";
        ALTER TABLE "users" DROP COLUMN "social_id";
        ALTER TABLE "users" DROP COLUMN "password_changed_at";
        ALTER TABLE "users" DROP COLUMN "deleted_at";
        ALTER TABLE "users" DROP COLUMN "login_fail_count";
        ALTER TABLE "users" DROP COLUMN "is_banned";
        ALTER TABLE "users" DROP COLUMN "terms_agreed_at";
        ALTER TABLE "users" DROP COLUMN "banned_by";
        ALTER TABLE "users" DROP COLUMN "is_deleted";
        ALTER TABLE "users" DROP COLUMN "banned_at";
        ALTER TABLE "users" DROP COLUMN "device_id";
        ALTER TABLE "users" ALTER COLUMN "gender" TYPE VARCHAR(6) USING "gender"::VARCHAR(6);"""


MODELS_STATE = (
    "eJztXWtzqsi6/itU6nyYXZW9Ro0mxtr7VBklK+4YdbysNWuGKTZCm7CD4ABmrZxd899Pdw"
    "NyawigctH+Itj028DTTV+efi//vVhrElCMT12gy+LLRYf574UqrAE8CVy5ZC6EzcZNRwmm"
    "sFRwVsHNszRMXRBNmLoSFAPAJAkYoi5vTFlTYaq6VRSUqIkwo6w+u0lbVf5zC3hTewbmC9"
    "Dhhd//gMmyKoEfwHD+bl75lQwUyfeosoTujdN5832D0waqeY8zorsteVFTtmvVzbx5N180"
    "dZdbVk2U+gxUoAsmQMWb+hY9Pno6+z2dN7Ke1M1iPaJHRgIrYauYntdNiIGoqQg/+DQGfs"
    "FndJe/N+rNm2b76rrZhlnwk+xSbv6yXs99d0sQIzCaX/yFrwumYOXAMLq4vQHdQI8UAq/3"
    "Iuhk9DwiAQjhgwchdACLw9BJcEF0G86BUFwLP3gFqM8mauCNVisGsy/dae+hO/0J5vobeh"
    "sNNmarjY/sSw3rGgLWBRJ9GilAtLNXE8B6rZYAQJgrEkB8zQ8gvKMJrG/QD+K/ZuMRGUSP"
    "SADIhQpf8HdJFs1LRpEN849ywhqDInpr9NBrw/hT8YL301P31yCuveH4DqOgGeazjkvBBd"
    "xBjFGXuXr1fPwoYSmIr98FXeJDV7SGFpU3fGndWAdTBFV4xlihN0bvZw8iCwN36KHBBafH"
    "Di1bmMNINLJcsNM+w23FmiDC39ZtvcOgOvgZJb/VP22kFbOYsVOYRao3UZabmya3XYJ689"
    "NFoL72KIpTOXWxGPSZySMqoV2DF6TrVhtlatZgkiDV6zCveNtESbUmc48zXtdgqtQSWrvS"
    "bm5EBmUU0Z8rsYn+3Ipt57ogreD5sl3bpYh16zZXIkpvYWmpjaRvBfETLmvVZqyS0R2X6F"
    "JTQrkb8GlUVRZfUf2gLM1VHR0aNetJJPSIAIktb1YifhARP/Wyhu7bqFmlo8eCT4FepIWL"
    "BRa2Bx7a7+TnExrdbxuNq6ubRu3qut1q3ty0YI06w3z4Utx4fzf4jIZ8X+fw8RwArAVZST"
    "N47QSqOXw1k4xezejBqxkau14E4wVI/EYwjO+aTmiv0VgSRKuJar3RTjIpaLSjJwXomh9Y"
    "p0NKg6hXJhOU9keeXy8QmFwlmlvFTK1CIKYFcB/wCm+HjST4NaLxa4Tw20AUAK9u10trqp"
    "IUx6BcNfGs15O0x3p0e6wH8VzKuvkiCe9hLPsQBzKWXpkAjnBcA6a8Bp/QSTkRjUGw352z"
    "AXzg80tRLY2FzQkjNIA3EFQRhJBypQtubxdP3SHbYdAvp96z1j/rGJxtF9MvCm9wRqTD8h"
    "TAp51khmU/nnAmGGpy+LhznHK6UBuaKAsKv9G1NzmybZORJogeZFSv/rhkI0Nquh/CSWyz"
    "1QDyKBNNRXuWVX4F1zUQqy2JhorsCkiimTqDTF1vbe+uYE9u2cVQAm+ySO5Ko9ujT4i2Rw"
    "dLHax0YLzwpvYKVB4tEtOASpauJLpHIesVwTB5/N2S56BoOhnxsfsk42ai6KSU+MbAOR88"
    "sbN592niY57RFBVdaeDU90DqT9cB5HeFMF8H8wcG/WV+G4/YIEG9yzf/7QI9k7A1NV7Vvv"
    "OC5H1tJ9lJ8i/NbNqEF18E9RlIvEDoueNrNKIIWrUFV61s8IJoym8E6uJO0xQgqBH0r1cu"
    "UItLKHisgXhHCh265u7G46Gv0u4Ggfn2aPF0x8IhBtcWzCSbEdNwhI20JvV6H0LqiOWIaF"
    "r1gaIglYAC0JunBtUjSGENwboUVDULqq4cBTVAvAkqrwPBIOl7zMGPiPWNX6oik8i4kZD9"
    "dR6/s74bCIfj0Wcne3C7PQStmmn64ROkk46CJx12bSwJ3HQcG+gTo0RgDBH4XTZfJF34Li"
    "gZeiKiMO2QiB2SCfQ1nLbBjyNTt0QQp51T0YtdXX4TxPfslUosgFZrwdVqrwIy1KdfklZk"
    "wRUpwkEpW0X6JQ9QkUVoDcB3kMaq8m63o4rUrN3kYyt2u5EyVqxfklZsoRWLHz6FOrSni5"
    "YNON8EvC4brwZhaWCL3z9OgSKYZOMIW9+5bxU1hSWVs7r/ctqwk+pWu0fhEQiK+QJn4aKm"
    "S3si8oDLmuKiKgzJWlPNF+UdYrLRdHNPTJ6swqa4rAqD4gxs4ougoC09sCcuPaecCmMCPx"
    "ogv0FQZPVNNg+GyACXVuZJXjwsBlBNCon/63FehN8IuimL8ga/+aHgmTiFHk87JVeQYF8j"
    "HhKfqV3eiYAjaus1UKWDNqGpr9STAOoN6PJKFg8K0xdPmRUGSTBNVNWqCOCADsR9p8LdXX"
    "E9VFqFgYHDFhy9NP2dh+PNek9YBk5hFQZko8ELPLyuGgfpkyeovLlbXIWhgatXEVlCyuIr"
    "MPmtIew9KZ7iEue4wAUqr8LowH7YXGombwDDOEgHjEqbWYVVGJbtRtEECa4ZkMHBnqDcwy"
    "IWuLzqzox/bHiAesk9ofh1w76Bys1+U5nphzgbWV1p0aiNVTDX4M/H2CHDfYu6GdglVrMp"
    "bQCB1U0PxwSUc5s/thWl8N/g5S0JbhwCtGa0N4cQlXpUf0G/Y+8RtnWBc2tccwgpQRG3is"
    "PP/0EdEBTlgCBYMVnMHoNlFG382B9079g5O+swzhmnPnybsNM5O5oNxqMO4/3Hqb3utD8Y"
    "f+nOeothd9ph/P8vktWm3y6lmcQspRltldIMGaXAb5Y3RE0n1FIfiPJaUCLsUXyCwW0wS/"
    "KTXUKpB2OiBS/bGzx1hz+1LhsBDUyvLwkCkgqcwkT43fi4vftLKLq1j8ZTCEGHsY6oNS/m"
    "uJHbJ5w6HcweOwz6hd/B4PMDbyXsTrO08NsEDfw2sn3fkjxQ6fJya8In4FdwSNJ0wvwy3h"
    "0VSb4o31QX/1htVbxcZpZbWYGPZXxCN/zfi6N8BwfzWOVnVjZbuBpUhY3xoqVyDhaWLFM9"
    "oNtWqR7wTI7P4C0wJJhfV3WhbxXw97f6HjAf23GQfwoaHlTjtYaCwlS/pGSKQ89bGbZ+WU"
    "3vXyIoSZXKY5TKPWu85Ah7hPKz1q8KuiEtKT/YYaTv4dxeflYfwXto2hpNH5UT5SjGBCbr"
    "wvcdP+BtQPD1LF1cPBbCNVu3z16Qe4IDQOfhWj57iy1db5AUyWBn54Nzxs6Z0WI4vPgria"
    "ZeSba5y4N1OrY4OynotsR4dtDXYpPRhPyufRyBMPw9xBx5VtZ/BOhEShFSipBShB9ShJTY"
    "KhexhdHkITpRtRLh68YvVk33lUdYs2uqJKOH4tEDhgGNtl8NS1YF07ytV/XQhCspxmFJij"
    "EZY0VeAcN8V5Au0iYV0R2WLBO1WjWK+0UzNrIpKPybbMimq6ib2vdJfEHUGUrAW6FsiIog"
    "r0lsRnT34pfKkcvexW4QRBRxQRBXdtQGFIThBoV9kFqtWxxvAsVtEG9x0IgGsGNDoKRWEy"
    "dZcRvEqzYqBaDoDdfCLWOFokClSO1dtAlYCrwuNVs4wkW7hcXbnrAOJe7qMhn64ckn/FYh"
    "6Lna+Z0JX+Az9SPwBEFTwGh+IGyAmJ8ekXXT3TJyDet5q1MlooIZgkCtZFp6+osoeu35lY"
    "VryHmHsY6c+rU7mKG/6MCpd8PxuM9PpuxstpiyHcb/37n+ebjojWe7y/ZfuFK969Z7cJWK"
    "Dpza7c0HXwbzbx3GOSsHm2Bsl3tVqFe+WD9BFw/jJ1gL6BeCP55NBnNEKzhnnHrfnc0Ho8"
    "8dxj7h1Ml4Nn9iUS7nLEulJPFNHO2ZOOSXeKPLa0F/598EZZtWCywke6KKYO0UimAGQKRA"
    "VkQJ0ntjWiofMFkghU9OUKWIprmc/FXhCQKd7nWSTjeoA+HpdK+D+HnnM+HmGKuREhCtpj"
    "5KRfRPnNeOVUAxtK0uZh8+d9I5LnSfuqOFPdQFw8mgCyigDDrC6RDbnXbvUFAZ54xTx71p"
    "h4E/JRgpVc0kAB/NLDj5qT9DIltJ/SwfhQWjPstOVPWQ+iw7iYoNWwJTXUeq61g+Xcdocj"
    "0PPnkFdIBqIIZSdrJcJmKV7dxH0TcLsIxejsqN3Qjfl3/Wte2Gt+NueBKEH1QxjdLOx+o7"
    "KO1MaefS0c5xIXEjDGj2C4NbdNi7I0S7DY4ofiRna0FRosPdBoWrZY901bi53o0K6E/cOD"
    "B76g6H4ZWyfwDOjp8lfH74qZoOISI3vthNDr8g3d9w8CC1wkRAElvgGQIpwnU2UsZN3yQD"
    "khTKHSCpG2VAkkIpoSikeoZG6RekQApvz5k21X1yFMa4LcQIrYT9tg2LnnpfJ1lPXkevJ6"
    "/xejKF+ukxGTJ/IAECPxaKNBDNjhEiHByaG3MI13cgwJ4M3Y9SXaWhujyVkqI38EtVU8km"
    "DkunR7iJ7BBuQkO817jZ2K6RVlwY0mj7myj5MlnhVM3BkU3948afoUoixGmNZK8R1yV/hv"
    "ogCtPayF4bG2mFnU+n3nsOCFaL+MrZkdEOhgxqG0FZqrhRNo0cqrlBNTeo5gbRezxhYRr2"
    "Lx+9MsUvGfBvf1R7QLoILWoR+gI/4BeTF9cpWT2f3Gmyeq3LoL5vNKv33YLj9TkljD45Cu"
    "N3Aa4b0jdGrxgFUTZ4Y629kgbsjzT7XTmq2B/Y/VBE7UVT4HBoCq+ZNZnCpeRoCTSy5+Eh"
    "l1wjFjnkGrGcOrRU1YaWptrTuM9O4Uy/wzhnnPrAdr986zD4cJFsnDuu/Sx4ViHU7/wL7A"
    "I0EqmRrGaIBeVaOXO+O5kMBz1kefVBNU2m7OdRdwRryjmz9Mwm3el88WRpmlnnnOovGJUQ"
    "ulHhCoIvgsFLsrCEc2mDXwlrWYmpz3ifPfEl0V4tDPwLLFw3gYocyu8P/gel0QoIjdXii6"
    "6pssijYMR28LR0gzahAAozcYcolVc2r0yZmO6q+WNbAyk6/G80/AExWgN77PxQo9QTpcCp"
    "UeopVGxJjVJPhwDdS3nso00QJ6bpkbdAjl0bx9kA2WtTY9r93NfE7RqoRFU77+XLuO0MXX"
    "jmJTtnMjW7C1g28zP269m64bZLqXaDXYW2kXvPmni7c/K5XCK/n2K9bjkBFSRuK9WuxU/B"
    "dfXeBXIqp4L1EkgSLBBdAgA5LL1ZYVeizRoz+fwFoBB5zL/f8PGnm+v23/6NSmy3cFntGr"
    "rXjYC8jjbrou11FDsqbeCnEMSdo1Lfg8HSORW2AWb2y/Cnf7sP8Y9//i/zP/V//81zj0Yd"
    "O05t32L3qaLHs2kSn5BOHbm2vJbmK8z4O1rooFj1b4A6hSwwbESwhrJQbaFCcqTZxvMHdk"
    "pg1z4vBn12OEAU2+4UWXP+giw5f+FUtr/oda1IBbtTzK0NehanBo+cikvvMO5Nio1TkLuq"
    "eeGKpY1aEjtPmCsSRHzND6Mpm0oqFHcCldTXPwqG4stWfeXxK4SRjOyfA1L5aezU9u6oG/"
    "XmTbN9dd3c9c+7lLhumeBRCmNggh+ENV5MaAyfVFU+5rgV3DGcoO3mMmForckUGVyfWADb"
    "kVbu4HEkbD0TxhB3ZwpoMpCOuHNlysTaVU1D2J3whue0H+wIuHI5bgTsJrwl3gegTOhJEG"
    "aUCT3Rit1FzCiBqecuWukFgXtyL17GMU87s5k8QmrA5ba5xTcyRG1j0ya439Icxs7Ogq/A"
    "c91EFlb4HYAqWeeUXSmMXcl5oVn4ar3eSOSVqRHjlqkR9vfgebIQlDGBqPxiFVm5571gEu"
    "HLP++hZeeVL9ovH/srO+0NkFM95wz55psjAg8fOHU2ZNlJh8EHTu0P2DkKLcvOEfHHz57G"
    "j9jTm3uO07vD3vhhjEOcOudIdsZ2Zyzf6yIff95/nPrE9gdzm1t0z5E/dqSFyT91R93P7B"
    "M72rkQ9CRlIRnrSayv69Hm1/WQ/TXyz7dvywiWUbCfv6/doVW79gmnThejEU6xT2DzmE9Z"
    "+OE8wBZin3Fq71tviHPZJzDX18HTE05yzvbniQ+sRGtNF7JWnCOcI4s/YadwwUyMauBc6j"
    "DOGad+no4X8DvGhxLA/awJyl4bKL4Ciu5G+4up3Xk5Z/ArGC9Qd4UPnNp9sv5aR3j1ge09"
    "wqvoUJbqyOLYyC94mnYn9VpZIwUVv02SaJckZpMk7PRNclxqZ5tb7cRz7Ir73cHwG6Efxu"
    "mwT0AHNJdhH4ffeLtf8P6ze2d+huwWdqdO6hOLiL2Zc8X+m2nWc5Vk1nMVPeu5IvYb8J4r"
    "mbB9EE2PB8QoQ56dIX8DuryylYT3GlCJBRU9sHqHSU6dPIznYzipQYcs7b+VoPm3Ilt/K+"
    "xyaQUBg4+fecLvLyHHHmvIfmGHfJ3QZ9lXOox9wqnWScNJaTgpV07KlZPSdFKaWWrnwA6x"
    "UMDypQwH7My14y8hz6n94m446JEm9vgC/ALwEdnADb5g20T7pASwuwRspoXUTjpHuKdsb7"
    "oYIE/1BMjdi3DVuzu34wywdpQBFk33nyZDds720ZTfPoWp3VGPHQ5xqnOaaeQ+uOt2VPxG"
    "0E1ZlDeCSopMHslpk0TzU0up7zF5PbBain/3ILzhFqFf5pOK22wrJ38dt2JCfVBAvcTZU0"
    "mBkFfm1PGhMQipkgPdC6dKDmdWsSFzL/8effINdr8c9WcX5wrSBOuNAnFIDXJAkPrbTO40"
    "0IEuDHhqx4E7fZu5p8zSoZ7Uhi7Qpnx2dDN2zowWw+EFqYs4AJLVd8Ho7/bSemH0TD/VNz"
    "iHIqz+7mzB+8cpUIQIlZBgwxzg0qqFrN+VUuyKOBMmE7fICgOD4kmu13BhFuXEIhM2U1+p"
    "lerOIkn4Q2HzxVNmpRuOISKlTVl8BSa/NYTnfXubKS5xjgtcoPIqhk4u+rp2Txyntet21g"
    "l0d3nPQHFkFV7rThA4ybF6xgkgoL5LVXSLUtH1VlAI6WhNh4BYJRUe6o1EyroxurohR6UW"
    "Kvvs3AaKyHHnpDfuk9w0omS0DdJnkdbnlO1hnVF0zLL3cZ0A8iBv4YmcdQIbVBN21CfvTt"
    "lXkKIfPkH7Uj12grehnDNOnbL/gtijNOeMU9lfJ7BG+kjxF59kqZkDK6GBHxsZThcyUHt+"
    "yQNQe6XSQysTk+e8dixHC4vaaBCpLCxtUJZWZsGVSXdSToJwJ1SsO7dPy7kHJCnrHse6+5"
    "cvKdYlPjnKuX8IcfrNI78chTj5tobotf091L5GOXuNxJR8oFckk/KEZpvfhkZ56NMgeP4v"
    "McFmkN07UuyCA0UEdgX7D/DugsSRkoHdkiTMZHDP5tDxo31dHXZ/Ggwf/Xvo2/f6GPA4C6"
    "XcZdHcpa5FeRf4mPtxZHNkfixjHwLxM/46wtaz6IDMp1E2ZDq9y05JtpRQdyeT6fiLTYR9"
    "yLLZmTuMc0Zm2YbsPQolBH859XHQe0RXrWMJ+DZxq+vIBakhwiEzXFfRy7+g3Fn6JFzLhg"
    "EkCMuWFK8kWnk+IHaW2P1Hk9VMlJJPkDJKJWOUFLAyM1SqR4yyvUWzvZQUzIWxKkd0i1NC"
    "l5JVF0clq2j0c7B39HOqMUiGOB+duCkQRPuJowmoXabLZOyTbufPQzPO56LBaoG4LQRpJi"
    "uRkkyF+bDcQ5mrLJ43hoNHFgVBfrRs2y3fe/ZJFu7iwG4G4L1MYqDQmHAArkhFdA/jFhbH"
    "8GxJbZGpLTLlO6gt8plVbElDT57S4jzSY1lalAnCFO0UVMhbYI14KDakumvPy8DyntDCKD"
    "mSBzmSEwfgsziNZwKCxqnJ+ICQoeyRWQHvwKPLmm77q/PMHSkVUBgV4K2RLHSAVz5fl3h4"
    "qd8n6kPMx5MOA3+QzsMuH3aP5/zh1PEEucFGPsidsyysQb2exN6uHm1vVw8SB/CrMNJFxX"
    "AlKG1ADohB17ensAwq3WbwKavW+/0IG7CLgVMH2XhNjTRBmIJNfWBR7YbTQjdmSU/XnknX"
    "nlGd7gHQ61vFTe3SStcPJMWQMJwkMMahTu4i4Mzg5K4gXaXyYhirqlQaA6ddc42jlLxtOg"
    "mZ5DSfPGgkb+A5N3w2pY4Ko45onEkaZ5LGmTy1OJPnFt+4nSRySTs6ckmbBjfOk8ulcTlL"
    "GpeT1zYRuuIfhNkLSZcp2h66YZWi7dlvw6eN8hmUq0jvc+xonzR4IQ1emL4fOYPghe4CPF"
    "Q5Hyliu3I56mHvFuBUDZtuUwNfIVQNm1ZscjXs0D5XEmPKHWF6KEvKUk7GIo0naZyOwk1L"
    "ferPcTsAQT3pJLsAIVvhQ3s42/idrln3A24MzjXMq0kJ3J75JYNmqYGrdGehqJ0Fuz4zzv"
    "td6fIusDh19jBgh/0OYx2zTOkP7BIt9FWFJypxJi/gfELiii9AfE1tg+qRyrbwKRW5e8B1"
    "j6Aa34Geijj0iByALcwCLIksRHetElm4edFMNLlQ0isbhkSpumGMuqHxgkVl9Q2opqa/p4"
    "Y7ogAKehzo1XPxmSqOTiIPnyXYItLBfwDuKPkspi1h2YpsTeS9MarIryC1s0+/0Fm6+rSI"
    "AzM1dCG5s0SPemShWwGUMaZbAWdWsSFam7qlzWdS72GC069ZQ7IUa2okVxIjOeoCGN1iTx"
    "fAgX2iQ8EYiPlTXUTDPSD1HJSvW2WfN96DbHy73oCrA62f/jdNQXxBa+lj+Jnu7kqvMETy"
    "WoC94H+05Z4IDVA5XnT+pS0rBkvu2hKeBpRUb8Lf5tJqUPCBDyJ/n92Gppu8pktOJDmqBF"
    "GEEkSmfbl9d+ROevrt2x1y23gI4OhtOJ/QWRK+lJk8CQIrzExSr7fU622JJnqXWb3eFuNm"
    "gzizJswXo2bg0ZNEa+7ve31nIXDkmaGrAgGzbqmn1oLngxXUZ/llwS6IDlqtCx3GOhL9KS"
    "x6PXY26zD2CafedwdDJGMdsyi2HNgGDo696D1DFRKttuhKlMnGuWpqi7iTRD2iQRwto42c"
    "Q4I5fgqG/KzIm8bfDXO7/PtbbQ+4/W26mcTmuRlt89wM2TwDXdd0fg0MQyDtRkQra4UEqa"
    "YWUVPLHU1D4MavoHyCdAFVsgUUHGH1bCtjvyQNMVx0iGFtvcGaaVlIjoAsrcyCK5PSGpTW"
    "oLRGVlqja5rIqBrWSg9Zr10QGI1glss4MkPYZeaxOdxRrIUdjQV8B48tb1RQmmA+Sm8U4k"
    "3UrQXimBtjVHk2hqdQEgjodd8JPFD0rpVfKr8RrL53mzzYttVSU7cGL6AeMbWpQkiWWisE"
    "XHUJsvLObzR4V15Yp7SjIQuf5d6q1dAy4kgWPksc6R71iVIsVCP90DOymMUbVfzdX/H3qF"
    "vOjjOAC9I+8+7iZezmsp1NPkYEB3clBmcO6/g1mGzw4M+tvNkAiS7CiluE/bkVVJMYDTQS"
    "Y6/IWS4tvE033Do/sIH2StJlRcAvkAjB0TPN4wKidCJXsokcGhBST+Q8QnQiRw036TS5Yt"
    "PkYAdwANQGdjHVRc3Tqe1jVWiIcPK9RYo3e5qITXFRc1l8BebCUeSpDrxHtQ/DrY202LJb"
    "Ycw6C+agMfLOcEF1SjHy7rq9x8/T8WLU7zDuOafeL6ajwXyBgtntTjl1ggLkTVB8vPmg94"
    "j+WMeLZLXnj1KXRMmxHq3kWA8pOeIjsU7IDd/JT2Oc0RhnR1cQ3eiySGid0Y5tnPxnudtj"
    "vmzXS1WQlWyebIni1LFqzPIST1nXwBTQqBcGO9r8ISRIrSCyW0HQCEzU7SLlGy8SbhxTt4"
    "unULHZIzC5ntPhwdnuzM6S+LZXy1fhhbAjE0D0kIOSL+O4kQ3Iwc8NZUCKYkDOa6V9+BC0"
    "8POwQCBi+DGD5JXP0d61PyaFMYCpHQb+cGqvi2Jcd+ecOhl2UYBrfMhCDh047qwBFCCiEd"
    "8w35VULTcsWRF+49gWxQp4A0oKPmOX/yz1ScStrqPAAj82KSDzC50nD6SZgpIONa/IWWL2"
    "slWfU3lAcwXyw6tdIsBERKwosgqMNBY4AanzhG6tkUI6RmLmZD9PsBTBMHlYOEArokzEBb"
    "kEao9etHMBSjGeAhNFKcYTrdiQ7+1yKFOeDleUgr4Ns5UfqV2OVTDX4M+RlS6PXRvHsUza"
    "j91FhqVzXVANO+AAieoN5rmM5X2xqarpZs9DQc7r9sEdT/8IBII3tK0uUr25AlnjfRjP/N"
    "lOsr4c252OOgz65dQZitvaYfChBCRnauvyIizKD9KOD2ecLyjYb42wMlMxJiG5sySa7B41"
    "4xftShf9TcPvaThkR59Zvt8dDL91mEACp7oJE3Y6GPe9WawUbx6kQzvxZsEJ3hxfWfZx+I"
    "2fdkeP3nyeZE7tzuewX+mOervHCqb48tyNR4uZLw9O4dRfFoPfkFPewW+wx5qPp/CJF6gL"
    "mbGw6/L9x/q9PKxndtrtzQfjEdb19SagaNT3WFfYOnIqO+/B7nDey9L/NepJ9tXq0ftq9d"
    "A+D25T6SOxe8WommCMmmCsinD0Llo1VYSDu8DJtoHj9oFDu2iUOToJgoHAHJWCYTilboia"
    "a1bWq0nY/pBANBCNFKOZBts80sT5PVaS+XEN8FSyPUwiqsEX2ZSyDIWxDG61EEfUyJ5XOh"
    "uPk3TScaKTDhqwPidjqZ3ieerePCBJcaY+T+gkumKTaGKXewDoet6yqotfcCxJ4DjGa3mz"
    "J4gVteIJghgcKMq0nIPt1Fxq5r3w5wVhHee5evlBoGyUj18JfxbnReWSBsYux6pNkNZy+l"
    "guXinK28fMpE7JZc2MnX4Z9NDulXXCqf3BjMX7WfaJZ6vNs73Gqd1eb7xAdkn2SZZNq9sE"
    "mwC3kVsAt8ENAAiGkXY3xStTVYu6I+ylCKrxnTSFjfZc40pUBcY4suIYXms8g2MI15jtVK"
    "/QWapGUEce1JEHpS0vqJb9GVVsdkcednjhPf132AvPJzdWcekm/4X48AjgEr1k9yD38bLd"
    "W2dHXrob8FZuKEWvijddrxe1Xte1KD8KHy8mHdmiF5ILuIDsMOiXU+/GcFkIf7IsCZtJfC"
    "tEu1YIrmPsL2svByHBMnJ0EuIsLAJgo+QOg3459b77S4eBP5w67X7uMPCHU2ffZnP2CS7q"
    "8TFLNVwnqIbgYOhWw3VINU9TTUDSp49eT3pE6IIyakGJVG0JI320h0mPSJl8S6IbVsm3JL"
    "z9SpaAStLYv1c0IbpNe8QCFbBCcmWeaRE1YsaLuyHLTKZsbzAb2Ejvps34on8pOmW7w5Df"
    "Azgx4t+AbqTk7kKCldSFPrw7Ibq4P4k1YHhxvxL+TL2t48rQTZ2YTR3/uiiFuYtPjirJpF"
    "CSsaEjjKAZlD3QOnrmFlg+yJMqK/gb1Mf6HitLN+AwCNqKBqXrE5KC53Z2PuBm7JwZLYbD"
    "gpU8nPYZzRp5WvDHrJHdUnLW1IctSaeUUdGUkSmb6Xxv7gQqOUeuJ3IbW4/xG1sPO471tO"
    "SU02S/JJ0ml2yaDCBoWarVK0f9wBXsBw6753Oo14ze/fzitEoLrlKnOsSUvlVCcmepBkMN"
    "OA49waIGHEe1gi5cJ6FEsB5VKeFeVsBio2iCfxEWvnoZt6zE0d22OGOyJeUFt5WuaiK3FW"
    "9uRAYeWmKL2y7bLZi0bEooaSm0mjBXTazB86ubGs6LUupXtU9IpAHgP7Fdx5nFenOXobFs"
    "w5TGbZMxTA0Fqt8I5guSgJ87ytvCeRsCLv4aPURLqqHr7Rq+i9D6FNz3LPvzcqogirBx81"
    "tdwZLNGvPzGkiy8POnT/ju7XoLS9TRn3odPTdo3cI/griUrFfBb51oSY9r2jOkKPYOt2WA"
    "TxVDchqELmNW+W6lhHBOprrgKyBHvYXx/IGdEhQXJtPx/WDI8oOnLjIn8P31+vT6wk4H94"
    "Ne13KcRU7n1Ml4Nue783m39/DE4hAp/gROHYx+WQym33yZwmnIE9dkPJ3zk/498sblnHMq"
    "fo8O475OWt38RhLV/Ea0Zn4jSFpouvwsq4LCpw0bFBKsilZFANFWEk+PMFc0pq1wSBu3y0"
    "4DaUCsmoC26knaKMwV7TyzHmql7kCWBk+/FIXTncnJ67hxIGLV7BWqJpiHD8uNB0RD/j/A"
    "L99N4oIkbis9LFwlJiJvxx4GrwOEFmmW+IHdjkcwR8OdtDtn1HKH7loc0nInsCBLzPH5Ba"
    "maTwqaz4YuP6qvvLoTgWZUKgWKrwC8Ku8zYJoKWAOVGEc3lOcyju36jnPzxi57Ys5LbK8Q"
    "fSM22i4lU1vWMHt0U0dU0grzM+ItYoRuBZT5Wrj9hGma+q1N7KD7Q6SRVLOFhcW2v0B0pQ"
    "6LEG9FTBS1mgIipcQmJnokxmpCJJarhE9IAxAXPTGLZpnsik6ztvCIHGZlcXSk/euKJMuK"
    "6FVFOCIu6kQyKZL4JOmUrARTshRGt8cc8X7dsG8RA51zKXZ8+7HhwVuaYU26xvsgV9ItU0"
    "fjwE2T+SdTZ3Ttu7X1gIYUQaw10Z9bCWcRm7v9DfFaquERBW+MBHdOSDsxR75dSq1Gp0Oj"
    "mx2FDUOv8P2y7nM4skVbwT6w3eH8gR+MJot5h/H+41T735cB+3V3Cf0J7Xt8C+14fLP2Oq"
    "wNDph//GRtZdgn3rgkmXYpkhjdNqKtbhshs1scuixNAGBXIMeQ5iVS7inDHCyMWZUmYZqI"
    "Q7xnmYUFROk0rATTMH+gHGm7AfwriHC5R65Vv9RB1N7zXaVcJ+mWr6O75etQt0xVCA89oa"
    "EqhBULpPLX/wObQQT5"
)
