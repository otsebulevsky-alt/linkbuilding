# Delivery Status Notification (Failure)

- **Date:** Fri, 05 Dec 2025 00:46:06 -0800 (PST)
- **From:** Mail Delivery Subsystem <mailer-daemon@googlemail.com>
- **To:** f.zakirkhojaeva@rantsports.com

---

Hello f.zakirkhojaeva@rantsports.com,

We're writing to let you know that the group you tried to contact (editor) may not exist, or you may not have permission to post messages to the group. A few more details on why you weren't able to post:

 * You might have spelled or formatted the group name incorrectly.
 * The owner of the group may have removed this group.
 * You may need to join the group before receiving permission to post.
 * This group may not be open to posting.

If you have questions related to this or any other Google Group, visit the Help Center at https://support.google.com/a/mg.co.za/bin/topic.py?topic=25838.

Thanks,

mg.co.za admins



----- Original message -----

X-Received: by 2002:a05:7022:f8c:b0:11a:126f:ee78 with SMTP id a92af1059eb24-11df0cae798mr6942179c88.34.1764924365268;
        Fri, 05 Dec 2025 00:46:05 -0800 (PST)
ARC-Seal: i=1; a=rsa-sha256; t=1764924365; cv=none;
        d=google.com; s=arc-20240605;
        b=F6OozibR2+8WZVPUitYloucthpz6EHfkfz7RpHp1zQN4cgCVjAFqeQnwmlm8+2WT64
         V5Ub2QytuWqh4muwtc0zO9ydosfuVkFQfVsysvhZMRv0hOT62Drp0OkLN0KyoQvBj5fm
         uI+w/vrjRJY3/8vaLUCtXf51W7L1zChkZ6arovYw2mfqF77GQ6pOEKP23Mmtf0J3LZdW
         XLbMsj40GiC3s2YyuEi5qSgMkmBqkm/bMDjFEX2TGCf4en1P6ItLylXlI3QwwUOUCHdO
         J0U5ajKJaeEvcvQmNGwVD6P5rMd5IupowkbAP2rXMv390e7RRNQ5PNHJfC4KyJ3DLTjF
         hiag==
ARC-Message-Signature: i=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=arc-20240605;
        h=to:subject:message-id:date:mime-version:reply-to:from
         :dkim-signature;
        bh=Q7s0KMvLwQMBXFHWWE2rnfjSvAfRxSnulC3tkOT+MU8=;
        fh=/XCFBk/MikoXgwPd+L/s9LV1YfgHqt98jjFYsILHMZ8=;
        b=bKSiQUjUTA3/QQKpwukm72R2SdYLIMrALxg3l/UvcqRsTkZR3rtEmtd5YP9f58DOS8
         G9gfcSb91emj5Ojteaz0IM2YJdh00hWGD67hSPNZ9+JwlBJA4Bpmk/DIIN02zjWMF7Rd
         vk2tvJkt2q5ZLzJYIiRzyuTWNCnd7X4EfiNGsTENrkGPA+iWs13qLXF6KLg6z85Mc1QJ
         YIOzFhXIqv7UB5gsBwM6Yw2McnWwJ55/gZrgB0LCNZzsMNEsmF7v4ZURn+3+ctEBr7F5
         t8rEoKvZNoUsomaPpyl5MCHxYgbL64T6GBTYAXzgatirrXpdAXBU/gKFi/S/rkJhIxD+
         3vqw==;
        dara=google.com
ARC-Authentication-Results: i=1; mx.google.com;
       dkim=pass header.i=@rantsports-com.20230601.gappssmtp.com header.s=20230601 header.b=WDcu3aAV;
       spf=pass (google.com: domain of f.zakirkhojaeva@rantsports.com designates 209.85.220.41 as permitted sender) smtp.mailfrom=f.zakirkhojaeva@rantsports.com;
       dara=neutral header.i=@mg.co.za
Return-Path: <f.zakirkhojaeva@rantsports.com>
Received: from mail-sor-f41.google.com (mail-sor-f41.google.com. [209.85.220.41])
        by mx.google.com with SMTPS id a92af1059eb24-11df75845c6sor832555c88.7.2025.12.05.00.46.05
        for <editor@mg.co.za>
        (Google Transport Security);
        Fri, 05 Dec 2025 00:46:05 -0800 (PST)
Received-SPF: pass (google.com: domain of f.zakirkhojaeva@rantsports.com designates 209.85.220.41 as permitted sender) client-ip=209.85.220.41;
Authentication-Results: mx.google.com;
       dkim=pass header.i=@rantsports-com.20230601.gappssmtp.com header.s=20230601 header.b=WDcu3aAV;
       spf=pass (google.com: domain of f.zakirkhojaeva@rantsports.com designates 209.85.220.41 as permitted sender) smtp.mailfrom=f.zakirkhojaeva@rantsports.com;
       dara=neutral header.i=@mg.co.za
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=rantsports-com.20230601.gappssmtp.com; s=20230601; t=1764924364; x=1765529164; darn=mg.co.za;
        h=to:subject:message-id:date:mime-version:reply-to:from:from:to:cc
         :subject:date:message-id:reply-to;
        bh=Q7s0KMvLwQMBXFHWWE2rnfjSvAfRxSnulC3tkOT+MU8=;
        b=WDcu3aAVdbqM0Uo6ARBlASsK6DgWIT2tcmNOXE+Zwlrcl0FUqc3X2DOihae1HHyFKK
         mikQGbshmobCy732WSzcycPCDmDgwvpCu/nwvGAmzQiCvXQDC7W8mNb+v839MA3qfFe1
         6C9hJzy3SPtMozESe37hty540ROqt3dN1RPmMP6HH3nULhf9YlsWuYUmxxKP3j1ZR8Q3
         bFofxw8N56vvd5JeUzC5lVcCg2EETqd+y3msls8k9vtOfVbaUqftPHqFilE23BdH1L42
         AMCgpNVkw7DG46cfCszflq+Og8Iho4L9zB0QgR791d792mZrJ75yiQIqwBNYYO1kRgGp
         XBjw==
X-Google-DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=1e100.net; s=20230601; t=1764924364; x=1765529164;
        h=to:subject:message-id:date:mime-version:reply-to:from:x-gm-gg
         :x-gm-message-state:from:to:cc:subject:date:message-id:reply-to;
        bh=Q7s0KMvLwQMBXFHWWE2rnfjSvAfRxSnulC3tkOT+MU8=;
        b=mFpdwHCFUumZzOWmWO37LjU3GD7ByPXOTfdQJVQVQYYLKW7kBzLd0Zffw1ymP5mE8U
         pIVUjoAjWUsn7gpWLeE2yft3fX7Ihivgi1CTC5UXGzwfxDnkPpLmAv7mLTZI83U5XZ3X
         jBbX9l34tjuDBbVN++hRG+nzo5cZOKTa5A5zb7f63KQzxo7RR+jsFIn6dqA7OrcvxEnM
         2FoC0VT9pXRz9iwfBmqEKUqb6rTMEDFvcxcmYjGDoh9faAmowlTP0sugJRnlV+X5hOB9
         xNVw6bHPCOrQDTqiwlpzLSU6+P1IIPYJ12u0n0hay5b0g5zODnaZ0yOYurqOTbfaTXI8
         htJg==
X-Gm-Message-State: AOJu0YylJGfrh5QIJK+hM85V99FsHr1RReGV2OM4w8kkdgKVwNK0vPOs
	7Gc1gdUBosCoKzP/Wlktk6lv9ljP12u2Xs9Wpjz3+FeppyHNhFVKDk7tgTpO1eRsMriDZlrcgWp
	mR0aPkXO7iprni0ZzgXVJ3lx+WkGGHsQSt6fN5g1CSB2d3DvmV/+o
X-Gm-Gg: ASbGncsIDiYOCay0Zs4uqMVQosvLGZpPMksWn6UXU34mIcFngOKbTpgs1TQHUFJd7hY
	cZuXEsAF/022KeAUkK70k5nAYqfHe9ZYJ38QAYE9EWXa9CUF80cW4+oedKeTu5+TVgAzB3aRKcu
	B5b8eacTMP2tNLlYoAEv0P74isxMyPDCrGMsiwr6yAuZH9Q7Da3YSXwGsXk/TXh6rcCl13NZSzR
	720/sBu5/cpkJiXeh7AUzqGdbPJcQ7AveTYiTp5JufGthRTn1rjNTh4Kz4muAd8MLRQ2hY=
X-Google-Smtp-Source: AGHT+IEHvb6tJGQ5SUILhjJb6Eu0yj8wOzfPqGJTzJXQzmVBpw9pAc0RG9aLoZCzYqXySRb1YTSPFzLNOjeUtyvWs4U=
X-Received: by 2002:a05:7022:698b:b0:119:e56c:18b8 with SMTP id
 a92af1059eb24-11df0cadf2fmr6859101c88.32.1764924363824; Fri, 05 Dec 2025
 00:46:03 -0800 (PST)
Received: from 8447955724 named unknown by gmailapi.google.com with HTTPREST;
 Fri, 5 Dec 2025 02:46:01 -0600
Received: from 8447955724 named unknown by gmailapi.google.com with HTTPREST;
 Fri, 5 Dec 2025 02:46:01 -0600
From: Feruza Zakirkhodjaeva <f.zakirkhojaeva@rantsports.com>
Reply-To: Feruza Zakirkhodjaeva <f.zakirkhojaeva@rantsports.com>
MIME-Version: 1.0
Date: Fri, 5 Dec 2025 02:46:01 -0600
X-Gm-Features: AWmQ_bkH-nuw-QpUfK4Q4om-vmdMDhvkUAXyKalMvSVXgzm8slHhKtaSYmfpjZo
Message-ID: <CAMoKwV5zYrxiX5+XeKh0To5gbhWWZVAUhp4ChZFO3ba+3D4L=w@mail.gmail.com>
Subject: Interest in collaborating with your website mg.co.za
To: editor@mg.co.za
Content-Type: multipart/alternative; boundary="000000000000c2ed5606453079ae"


