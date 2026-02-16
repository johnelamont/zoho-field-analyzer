import requests

session = requests.Session()

url = "https://crm.zoho.com/crm/v6/settings/modules"
params = {
    'include': 'team_spaces',
    'status': 'user_hidden,system_hidden,scheduled_for_deletion,visible'
}

headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'referer': 'https://crm.zoho.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'x-crm-org': '708002562',
    'x-requested-with': 'XMLHttpRequest',
    'x-static-version': '12593739',
    'x-zcsrf-token': 'crmcsrfparam=fdb5daf9ce9ffd1e112c98d06942487a9769bf9d5a59cb9dcf02ccc7f5bc016e6d54ea1e1a392e73c639b258b4a16810717c291a331e1a83c365e59724e3cb36',
    'Cookie': 'zVisitCount=0; drecn=2745ec6b7c663026a5d4bd2c2b36d2506691b4a1ae8da03fc39f6973d038f8a93fdbb3489430167a489e80713327fe99656cd05c6539ab6b5687c36e06a1b8d5; zalb_dd6072214d=c822465db482dbbe5bb0e403058e5353; zalb_3309580ed5=86e8a70654682624777345aa347b91ae; zalb_8b7213828d=86e1df9d631368310b26f28cbc66a048; zalb_c9d678d763=67e70f7a01422dc0b324b7276c23f747; zalb_6e4b8efee4=f7a091aeefc4a3e48430e0d12e231707; zalb_c3214d0e02=f4a63eb03ba4c1ac1922898bb889a676; zalb_ae6d309649=6d50a558602a5937169102c894284afe; group_name=usergroup3; 1769693652817=true; ZW_CSRF_TOKEN=cb91c92119aab0278ea824173f6e3011d56044b699b3a5ae7b2b25cec04653627e1e2e975a2ad0dee2db256e1be8906a04b3edda91557808c119dafb2faaf791; zalb_c331a7426a=6483666beac48f1382b4585bfbe8cbd1; CROSSCDNID=bca1c1999c9112dc4528ef78d10ba93878cc8967ff6345f4e7016e14369e84e226520b820f0a58c1b7f10dce4f79d26d; CROSSCDNCOUNTRY=US; JSESSIONID=59B981CE994CB901345FE457304B98F5; __Secure-iamsdt=0.EnQSMGyoMz5XkOOL8n_RA38O4v7IbKNWdNJFrsZS9IJOHSG0RwO6q7LUYMfFzKch88kgpBpA-1NLH81At1NFHkY2nQyXBePD5UnTfuZ2_RORDlDxPYNWMfD_5_Lh29PZDa3GOk7NhhU-x4_RSPI6VgB6-Ddjtw; _iamadt=6ca8333e5790e38bf27fd1037f0ee2fec86ca35674d245aec652f4824e1d21b44703baabb2d460c7c5cca721f3c920a4; _iambdt=fb534b1fcd40b753451e46369d0c9705e3c3e549d37ee676fd13910e50f13d835631f0ffe7f2e1dbd3d90dadc63a4ecd86153ec78fd148f23a56007af83763b7; crmcsr=fdb5daf9ce9ffd1e112c98d06942487a9769bf9d5a59cb9dcf02ccc7f5bc016e6d54ea1e1a392e73c639b258b4a16810717c291a331e1a83c365e59724e3cb36; _zcsr_tmp=fdb5daf9ce9ffd1e112c98d06942487a9769bf9d5a59cb9dcf02ccc7f5bc016e6d54ea1e1a392e73c639b258b4a16810717c291a331e1a83c365e59724e3cb36; CSRF_TOKEN=fdb5daf9ce9ffd1e112c98d06942487a9769bf9d5a59cb9dcf02ccc7f5bc016e6d54ea1e1a392e73c639b258b4a16810717c291a331e1a83c365e59724e3cb36; CT_CSRF_TOKEN=fdb5daf9ce9ffd1e112c98d06942487a9769bf9d5a59cb9dcf02ccc7f5bc016e6d54ea1e1a392e73c639b258b4a16810717c291a331e1a83c365e59724e3cb36; wms-tkp-token=4405836-21307f80-00a0112fa1b8d6d9ba66243d7016c2b8; com_chat_owner=1771176419091; com_avcliq_owner=1771176419091; zalb_zid=708002562'
}

r = requests.get(url, params=params, headers=headers)
print("Status:", r.status_code)
print("Content-Type:", r.headers.get('Content-Type'))
print("Response:", r.text[:500])