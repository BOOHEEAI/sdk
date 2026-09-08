//go:build ignore

// 流式图片识别示例
//
// 用法:
//
//	go run food_image_recognize_stream.go                              # 默认图片
//	go run food_image_recognize_stream.go --url https://xxx.jpg        # 按URL识别
//	go run food_image_recognize_stream.go --base64 /path/to/image.jpg  # 按base64识别
//	go run food_image_recognize_stream.go --url https://xxx.jpg --ingredients sugar,purine --with-nrv
package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"strings"

	boohee "github.com/BOOHEEAI/sdk/go"
)

type FoodImageRecognizeStreamReq struct {
	ImageURL    string
	ImageData   string
	Ingredients string
	WithNrv     bool
}

func (r *FoodImageRecognizeStreamReq) Method() boohee.HttpMethod { return boohee.MethodPost }
func (r *FoodImageRecognizeStreamReq) URL() string {
	return "/open-apis/v1/food/image_recongize_stream"
}
func (r *FoodImageRecognizeStreamReq) QueryParams() url.Values { return nil }
func (r *FoodImageRecognizeStreamReq) Body() any {
	body := map[string]any{}
	if r.ImageURL != "" {
		body["image_url"] = r.ImageURL
	}
	if r.ImageData != "" {
		body["image_data"] = r.ImageData
	}
	if r.Ingredients != "" {
		body["ingredients"] = r.Ingredients
	}
	if r.WithNrv {
		body["with_nrv"] = true
	}
	return body
}

func loadEnv() {
	data, err := os.ReadFile("../../.env")
	if err != nil {
		fmt.Println("请先复制 .env.example 为 .env 并填入真实凭证")
		os.Exit(1)
	}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) == 2 {
			os.Setenv(strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1]))
		}
	}
}

func parseArgs() (imageURL, imageData, ingredients string, withNrv bool) {
	args := os.Args[1:]
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--url":
			imageURL = args[i+1]
			i++
		case "--base64":
			data, err := os.ReadFile(args[i+1])
			if err != nil {
				fmt.Printf("读取文件失败: %v\n", err)
				os.Exit(1)
			}
			imageData = base64.StdEncoding.EncodeToString(data)
			i++
		case "--ingredients":
			ingredients = args[i+1]
			i++
		case "--with-nrv":
			withNrv = true
		}
	}
	return
}

func main() {
	loadEnv()

	apiKey := os.Getenv("BOOHEE_API_KEY")
	if apiKey == "" {
		fmt.Println("BOOHEE_API_KEY 未配置")
		os.Exit(1)
	}

	baseURL := os.Getenv("BOOHEE_BASE_URL")
	if baseURL == "" {
		baseURL = "https://api.boohee.com"
	}

	client, err := boohee.NewClient(boohee.ClientConfig{
		AuthMode: boohee.AuthModeAPIKey,
		APIKey:   apiKey,
		BaseURL:  baseURL,
	})
	if err != nil {
		fmt.Printf("创建客户端失败: %v\n", err)
		os.Exit(1)
	}

	imageURL, imageData, ingredients, withNrv := parseArgs()
	if imageURL == "" && imageData == "" {
		imageURL = "https://img.boohee.cn/ghp/foods/000/000/001/140_1.jpg"
	}

	label := imageURL
	if label == "" {
		label = "base64数据"
	}
	fmt.Printf("识别图片: %s\n\n", label)
	fmt.Println("流式输出:")

	var fullContent strings.Builder
	var foodInfo []any

	err = client.ExecuteStream(&FoodImageRecognizeStreamReq{
		ImageURL: imageURL, ImageData: imageData,
		Ingredients: ingredients, WithNrv: withNrv,
	}, func(data string) {
		var event map[string]any
		if err := json.Unmarshal([]byte(data), &event); err != nil {
			return
		}
		resultCode, _ := event["result_code"].(float64)
		if resultCode != 0 {
			msg, _ := event["message"].(string)
			fmt.Printf("\n错误: %s\n", msg)
			os.Exit(1)
		}
		inner, ok := event["data"].(map[string]any)
		if !ok {
			return
		}
		if content, ok := inner["content"].(string); ok && content != "" {
			fmt.Print(content)
			fullContent.WriteString(content)
		}
		if end, ok := inner["end"].(bool); ok && end {
			if fi, ok := inner["food_info"].([]any); ok {
				foodInfo = fi
			}
		}
	})
	if err != nil {
		fmt.Printf("\n请求失败: %v\n", err)
		os.Exit(1)
	}

	fmt.Println()

	if len(foodInfo) > 0 {
		fmt.Printf("\n--- 识别到 %d 个食物 ---\n\n", len(foodInfo))
		for _, f := range foodInfo {
			food := f.(map[string]any)
			fmt.Printf("  %s  估重: %vg  热量: %vkcal/100g  蛋白质: %vg/100g  脂肪: %vg/100g  碳水: %vg/100s\n",
				food["name"], food["amount"], food["calories"],
				food["protein"], food["fat"], food["carbohydrate"])
			if ings, ok := food["ingredients"].([]any); ok && len(ings) > 0 {
				var ingStrs []string
				for _, ing := range ings {
					i := ing.(map[string]any)
					ingStrs = append(ingStrs, fmt.Sprintf("%s: %v%s", i["name"], i["value"], i["unit"]))
				}
				fmt.Printf("    营养素: %s\n", strings.Join(ingStrs, ", "))
			}
			if nrvs, ok := food["nrv"].([]any); ok && len(nrvs) > 0 {
				var nrvStrs []string
				for _, n := range nrvs {
					nrv := n.(map[string]any)
					nrvStrs = append(nrvStrs, fmt.Sprintf("%s: %v", nrv["name"], nrv["value"]))
				}
				fmt.Printf("    NRV: %s\n", strings.Join(nrvStrs, ", "))
			}
			fmt.Println()
		}
	}
}
