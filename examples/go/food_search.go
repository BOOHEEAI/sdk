//go:build ignore

// 食物检索示例
//
// 用法:
//
//	go run food_search.go                    # 默认搜索"苹果"
//	go run food_search.go 米饭               # 按关键词搜索
//	go run food_search.go --barcode 6901236  # 按条码搜索
//	go run food_search.go 苹果 --sort calorie_asc --with-units
package main

import (
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"strings"

	boohee "github.com/BOOHEEAI/sdk/go"
)

var healthLight = map[int]string{
	0: "无",
	1: "🟢绿灯",
	2: "🟡黄灯",
	3: "🔴红灯",
}

type FoodSearchReq struct {
	Keyword   string
	Barcode   string
	Page      int
	PerPage   int
	Sort      string
	WithUnits bool
}

func (r *FoodSearchReq) Method() boohee.HttpMethod { return boohee.MethodGet }
func (r *FoodSearchReq) URL() string               { return "/open-apis/v1/food/search" }
func (r *FoodSearchReq) QueryParams() url.Values {
	params := url.Values{
		"page":     {fmt.Sprintf("%d", r.Page)},
		"per_page": {fmt.Sprintf("%d", r.PerPage)},
	}
	if r.Keyword != "" {
		params.Set("keyword", r.Keyword)
	}
	if r.Barcode != "" {
		params.Set("barcode", r.Barcode)
	}
	if r.Sort != "" {
		params.Set("sort", r.Sort)
	}
	if r.WithUnits {
		params.Set("with_units", "true")
	}
	return params
}
func (r *FoodSearchReq) Body() any { return nil }

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

func parseArgs() (keyword, barcode, sort string, page, perPage int, withUnits bool) {
	page = 1
	perPage = 20
	args := os.Args[1:]
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--barcode":
			barcode = args[i+1]
			i++
		case "--sort":
			sort = args[i+1]
			i++
		case "--with-units":
			withUnits = true
		case "--page":
			fmt.Sscanf(args[i+1], "%d", &page)
			i++
		case "--per-page":
			fmt.Sscanf(args[i+1], "%d", &perPage)
			i++
		default:
			if keyword == "" {
				keyword = args[i]
			}
		}
	}
	return
}

func main() {
	loadEnv()

	// ACCESS_TOKEN 模式
	appID := os.Getenv("BOOHEE_APP_ID")
	appKey := os.Getenv("BOOHEE_APP_KEY")
	privateKeyPath := os.Getenv("BOOHEE_PRIVATE_KEY_PATH")
	if appID == "" || appKey == "" || privateKeyPath == "" {
		fmt.Println("ACCESS_TOKEN 模式需要配置 BOOHEE_APP_ID, BOOHEE_APP_KEY, BOOHEE_PRIVATE_KEY_PATH")
		os.Exit(1)
	}

	privateKey, err := os.ReadFile(privateKeyPath)
	if err != nil {
		fmt.Printf("读取私钥失败: %v\n", err)
		os.Exit(1)
	}

	baseURL := os.Getenv("BOOHEE_BASE_URL")
	if baseURL == "" {
		baseURL = "https://api.boohee.com"
	}

	client, err := boohee.NewClient(boohee.ClientConfig{
		AppID:      appID,
		AppKey:     appKey,
		PrivateKey: string(privateKey),
		BaseURL:    baseURL,
	})
	if err != nil {
		fmt.Printf("创建客户端失败: %v\n", err)
		os.Exit(1)
	}

	keyword, barcode, sort, page, perPage, withUnits := parseArgs()
	if keyword == "" && barcode == "" {
		fmt.Println("keyword 和 barcode 至少传入一个")
		os.Exit(1)
	}

	label := keyword
	if label == "" {
		label = barcode
	}
	fmt.Printf("搜索: %s\n\n", label)

	resp, err := client.Execute(&FoodSearchReq{
		Keyword: keyword, Barcode: barcode,
		Page: page, PerPage: perPage,
		Sort: sort, WithUnits: withUnits,
	})
	if err != nil {
		fmt.Printf("请求失败: %v\n", err)
		os.Exit(1)
	}
	if !resp.IsSuccess() {
		fmt.Printf("API 错误: %v\n", resp.Err())
		os.Exit(1)
	}

	var data map[string]any
	if err := json.Unmarshal(resp.Data, &data); err != nil {
		fmt.Printf("解析响应失败: %v\n", err)
		os.Exit(1)
	}

	foods, _ := data["foods"].([]any)
	for _, f := range foods {
		food := f.(map[string]any)
		name, _ := food["name"].(string)
		hl, _ := food["health_light"].(float64)
		light := healthLight[int(hl)]
		liquid := ""
		if isLiquid, ok := food["is_liquid"].(bool); ok && isLiquid {
			liquid = " [液体]"
		}
		fmt.Printf("  %s%s  %s\n", name, liquid, light)
		fmt.Printf("    热量: %vkcal  蛋白质: %vg  脂肪: %vg  碳水: %vg\n",
			food["calories"], food["protein"], food["fat"], food["carbohydrate"])
		if img, ok := food["image_url"].(string); ok && img != "" {
			fmt.Printf("    图片: %s\n", img)
		}
		if units, ok := food["units"].([]any); ok && len(units) > 0 {
			var unitStrs []string
			for j, u := range units {
				if j >= 3 {
					break
				}
				unit := u.(map[string]any)
				unitStrs = append(unitStrs, fmt.Sprintf("%v(%vg)", unit["unit_name"], unit["weight"]))
			}
			fmt.Printf("    常用单位: %s\n", strings.Join(unitStrs, ", "))
		}
		fmt.Println()
	}

	respPage := int(data["page"].(float64))
	respPerPage := int(data["per_page"].(float64))
	hasMore, _ := data["has_more"].(bool)
	more := ""
	if hasMore {
		more = "  有下一页"
	}
	fmt.Printf("第 %d 页, 每页 %d 条, 共 %d 条%s\n", respPage, respPerPage, len(foods), more)
}
