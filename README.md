# 🚀 Infra Power Monitor

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![Version](https://img.shields.io/badge/version-1.2.3-blue.svg)

Control unificado de encendido, apagado y monitorización de salud para servidores y estaciones de trabajo en Home Assistant. Soporta protocolos industriales como **iDRAC** y **Redfish**, además de un modo **Híbrido (WoL + SSH)** ultra-eficiente.

---

## ✨ Características Principales

*   **Panel Premium Automático**: Una interfaz dedicada con diseño profesional, colores dinámicos según el estado y optimizada para móvil.
*   **Control Total**: Encendido, Apagado, Reinicio y Refresco manual de datos.
*   **Monitorización en Tiempo Real**: Estado de salud, temperatura de CPU y versión de firmware.
*   **Modo Híbrido Exclusivo**: Enciende por Wake-on-LAN y apaga/reinicia mediante un script optimizado vía SSH (sin necesidad de dejar contraseñas guardadas).
*   **Integración Nativa**: Crea sensores y botones estándar para que los uses en tus propias automatizaciones o dashboards.

---

## 🛠️ Instalación

### Opción 1: HACS (Recomendado)
1. Abre **HACS** en tu Home Assistant.
2. Haz clic en los tres puntos de la esquina superior derecha y selecciona **Repositorios personalizados**.
3. Añade la URL de este repositorio y selecciona la categoría **Integración**.
4. Busca `Infra Power Monitor` e instálalo.
5. **Reinicia Home Assistant**.

---

## ⚙️ Configuración

Una vez instalada, ve a **Ajustes > Dispositivos y Servicios > Añadir Integración** y busca `Infra Power Monitor`.

### Métodos de Conexión:
*   **iDRAC**: Para servidores Dell con licencia Enterprise/Express.
*   **Redfish**: Estándar moderno para servidores HP (iLO), Supermicro, Lenovo, etc.
*   **Wake-on-LAN**: Control básico de encendido para cualquier PC.
*   **Híbrido (WoL + SSH)**: La mejor opción para estaciones de trabajo (Linux/Windows). Permite apagado seguro instalando un pequeño helper automático.

---

## 📱 Uso del Panel

Esta integración incluye un panel lateral dedicado llamado **Infra Power Monitor**. 

*   **¿No quieres el menú lateral?** Puedes desactivarlo yendo a la configuración de la integración y desmarcando la opción "Activar panel lateral".
*   **Navegación Móvil**: El panel incluye un botón de menú superior para que puedas moverte por Home Assistant sin problemas desde la App.
*   **Colores de Estado**:
    *   🟢 **Verde**: Encendido y funcionando.
    *   🔘 **Gris**: Apagado.
    *   🔵 **Azul**: Procesando (Arrancando o Reiniciando).

---

## 📄 Créditos y Soporte
Desarrollado para la monitorización de infraestructura crítica en entornos domésticos y profesionales. Si encuentras un error, por favor abre un *Issue* en el repositorio.

---
*Nota: Se recomienda tener instaladas las tarjetas `stack-in-card` y `button-card` de HACS para disfrutar de la experiencia visual completa.*