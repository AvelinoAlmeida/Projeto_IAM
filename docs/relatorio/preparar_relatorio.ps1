# ============================================================
#  Preparar imagens e compilar o relatório LaTeX para PRISM
# ============================================================

Write-Host "=== Preparar relatório IAM (LaTeX) ===" -ForegroundColor Cyan

# Criar pasta docs/imagens/ na raiz do projeto
$imagesDir = ".\docs\imagens"
if (-not (Test-Path $imagesDir)) {
    New-Item -ItemType Directory -Path $imagesDir | Out-Null
    Write-Host "[OK] Pasta 'docs/imagens/' criada." -ForegroundColor Green
}

# Caminhos dos SVGs originais
$svgs = @{
    "arquitetura_iam"    = ".\app\static\report-assets\arquitetura_iam.svg"
    "evidencias_dashboard" = ".\app\static\report-assets\evidencias_dashboard.svg"
    "fluxo_jml"          = ".\app\static\report-assets\fluxo_jml.svg"
    "matriz_rbac"        = ".\app\static\report-assets\matriz_rbac.svg"
}

# Opção A: Inkscape (se instalado)
$inkscape = Get-Command inkscape -ErrorAction SilentlyContinue
if ($inkscape) {
    Write-Host "[INFO] Inkscape encontrado. A converter SVG → PNG..." -ForegroundColor Yellow
    foreach ($name in $svgs.Keys) {
        $src = $svgs[$name]
        $dst = "$imagesDir\$name.png"
        inkscape --export-type=png --export-dpi=150 --export-filename="$dst" "$src"
        Write-Host "  -> $name.png" -ForegroundColor Green
    }
}
# Opção B: rsvg-convert (librsvg)
elseif (Get-Command rsvg-convert -ErrorAction SilentlyContinue) {
    Write-Host "[INFO] rsvg-convert encontrado. A converter SVG → PNG..." -ForegroundColor Yellow
    foreach ($name in $svgs.Keys) {
        $src = $svgs[$name]
        $dst = "$imagesDir\$name.png"
        rsvg-convert -d 150 -p 150 -f png -o "$dst" "$src"
        Write-Host "  -> $name.png" -ForegroundColor Green
    }
}
# Opção C: Python (cairosvg)
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "[INFO] A usar Python + cairosvg para converter SVG → PNG..." -ForegroundColor Yellow
    pip install cairosvg -q
    foreach ($name in $svgs.Keys) {
        $src = $svgs[$name]
        $dst = "$imagesDir\$name.png"
        python -c "import cairosvg; cairosvg.svg2png(url='$src', write_to='$dst', dpi=150)"
        Write-Host "  -> $name.png" -ForegroundColor Green
    }
}
else {
    Write-Host "[AVISO] Nenhuma ferramenta de conversão encontrada." -ForegroundColor Red
    Write-Host "  Converta manualmente os SVGs em PNG (150 dpi) para a pasta docs/imagens/:" -ForegroundColor Yellow
    foreach ($name in $svgs.Keys) {
        Write-Host "    $($svgs[$name]) -> docs\imagens\$name.png"
    }
}

Write-Host ""
Write-Host "=== Instruções para compilar no PRISM / Overleaf ===" -ForegroundColor Cyan
Write-Host "1. Acede a https://prism.openai.com (ou Overleaf)" -ForegroundColor White
Write-Host "2. Carrega o ficheiro: docs/relatorio/relatorio_iam.tex" -ForegroundColor White
Write-Host "3. Carrega as imagens PNG da pasta docs/imagens/ para o projeto" -ForegroundColor White
Write-Host "4. Compila com pdflatex (2x para o índice)" -ForegroundColor White
Write-Host ""
Write-Host "=== Compilação local (se tiveres MiKTeX/TeX Live) ===" -ForegroundColor Cyan
Write-Host "pdflatex relatorio_iam.tex" -ForegroundColor Gray
Write-Host "pdflatex relatorio_iam.tex  # segunda vez para índice" -ForegroundColor Gray
