from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import base64
import hashlib
import hmac


@csrf_exempt
def webhook(request):
    print("Whouau !!!!")
    secret_key = '1234'
    if request.method == 'POST':
        # On valide la siganture
        signature = request.META.get('HTTP_X_EXL_SIGNATURE')
        if not signature: 
                return HttpResponse(status=500)
        body = request.body
        key = secret_key.encode('utf-8')
        received_hmac_b64 = signature.encode('utf-8')
        generated_hmac = hmac.new(key=key, msg=body, digestmod=hashlib.sha256).digest()
        generated_hmac_b64 = base64.b64encode(generated_hmac)
        match = hmac.compare_digest(received_hmac_b64, generated_hmac_b64)
        if not match: 
                return HttpResponse(status=500)

        print(request.body)
        return HttpResponse('Hello, world. This is the webhook response.')
    else :
        print("Whololo !!!!")
        return HttpResponse(status=200)