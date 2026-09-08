#!/usr/bin/env python3
"""流式图片识别示例

用法:
  python food_image_recognize_stream.py                              # 默认图片
  python food_image_recognize_stream.py --url https://xxx.jpg        # 按URL识别
  python food_image_recognize_stream.py --base64 /path/to/image.jpg  # 按base64识别
  python food_image_recognize_stream.py --url https://xxx.jpg --ingredients sugar,purine --with-nrv
"""
import os
import sys
import json
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../python'))

from boohee_sdk import BooheeClient, AuthMode, BaseReq, HttpMethod


class FoodImageRecognizeStreamReq(BaseReq):
    def __init__(self, image_url=None, image_data=None, ingredients=None, with_nrv=False):
        self.image_url = image_url
        self.image_data = image_data
        self.ingredients = ingredients
        self.with_nrv = with_nrv

    def get_method(self) -> HttpMethod:
        return HttpMethod.POST

    def get_url(self) -> str:
        return '/open-apis/v1/food/image_recongize_stream'

    def get_body(self):
        body = {}
        if self.image_url:
            body['image_url'] = self.image_url
        if self.image_data:
            body['image_data'] = self.image_data
        if self.ingredients:
            body['ingredients'] = self.ingredients
        if self.with_nrv:
            body['with_nrv'] = True
        return body


def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '../../.env')
    if not os.path.exists(env_path):
        print("请先复制 .env.example 为 .env 并填入真实凭证")
        sys.exit(1)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())


def parse_args():
    args = sys.argv[1:]
    opts = {}
    i = 0
    while i < len(args):
        if args[i] == '--url':
            opts['image_url'] = args[i + 1]; i += 2
        elif args[i] == '--base64':
            filepath = args[i + 1]
            with open(filepath, 'rb') as f:
                opts['image_data'] = base64.b64encode(f.read()).decode()
            i += 2
        elif args[i] == '--ingredients':
            opts['ingredients'] = args[i + 1]; i += 2
        elif args[i] == '--with-nrv':
            opts['with_nrv'] = True; i += 1
        else:
            i += 1
    return opts


def main():
    load_env()

    api_key = os.environ.get('BOOHEE_API_KEY')
    if not api_key:
        print("BOOHEE_API_KEY 未配置")
        sys.exit(1)

    client = BooheeClient(
        api_key=api_key,
        auth_mode=AuthMode.API_KEY,
        base_url=os.environ.get('BOOHEE_BASE_URL', 'https://api.boohee.com'),
    )
    opts = parse_args()

    if not opts.get('image_url') and not opts.get('image_data'):
        opts['image_url'] = 'https://img.boohee.cn/ghp/foods/000/000/001/140_1.jpg'

    label = opts.get('image_url') or 'base64数据'
    print(f"识别图片: {label}\n")
    print("流式输出:")

    full_content = ''
    food_info = []

    for chunk in client.execute_stream(FoodImageRecognizeStreamReq(**opts)):
        try:
            event = json.loads(chunk)
            result_code = event.get('result_code', -1)
            if result_code != 0:
                print(f"\n错误: {event.get('message', 'unknown')}")
                sys.exit(1)

            data = event.get('data', {})
            content = data.get('content', '')
            if content:
                print(content, end='', flush=True)
                full_content += content

            if data.get('end'):
                food_info = data.get('food_info', [])
        except json.JSONDecodeError:
            pass

    print("\n")

    if food_info:
        print(f"--- 识别到 {len(food_info)} 个食物 ---\n")
        for food in food_info:
            print(f"  {food.get('name', '?')}  "
                  f"估重: {food.get('amount', '?')}g  "
                  f"热量: {food.get('calories', '?')}kcal/100g  "
                  f"蛋白质: {food.get('protein', '?')}g  "
                  f"脂肪: {food.get('fat', '?')}g  "
                  f"碳水: {food.get('carbohydrate', '?')}g")
            ingredients = food.get('ingredients', [])
            if ingredients:
                ing_strs = [f"{i['name']}: {i['value']}{i['unit']}" for i in ingredients]
                print(f"    营养素: {', '.join(ing_strs)}")
            nrv = food.get('nrv', [])
            if nrv:
                nrv_strs = [f"{n['name']}: {n['value']}" for n in nrv]
                print(f"    NRV: {', '.join(nrv_strs)}")
            print()


if __name__ == '__main__':
    main()
