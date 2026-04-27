# 🚀 Infra Power Monitor

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![Version](https://img.shields.io/badge/version-1.2.6-blue.svg)

Control unificado de encendido, apagado y monitorización de salud para servidores y estaciones de trabajo en Home Assistant. Soporta protocolos industriales como **iDRAC** y **Redfish**, además de un modo **Híbrido (WoL + SSH)** ultra-eficiente.

---

## ✨ Características Principales

*   **Panel Premium Nativo**: Interfaz profesional integrada, fluida y **sin dependencias externas**.
*   **Zero Extras**: **NO necesitas instalar nada más** (ni `button-card`, ni `stack-in-card`). Todo está incluido en el paquete para una carga instantánea.
*   **Control Total**: Encendido, Apagado, Reinicio y Refresco manual de datos.
*   **Monitorización en Tiempo Real**: Estado de salud, temperatura de CPU y versión de firmware.
*   **Optimización Extrema**: El panel carga inmediatamente y no ralentiza tu Home Assistant gracias a su nueva arquitectura de caché.

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
*   **Híbrido (WoL + SSH)**: La mejor opción para estaciones de trabajo (Linux/Windows).

---

## 📱 Uso del Panel

Esta integración incluye un panel lateral dedicado llamado **Infra Power Monitor**. 

*   **¿No quieres el menú lateral?** Ve a **Ajustes > Dispositivos y Servicios > Infra Power Monitor**, pulsa en el botón **CONFIGURAR** y desactiva la opción "Activar panel en la barra lateral".
*   **Navegación Móvil**: El panel incluye un botón de menú superior para moverte por HA fácilmente.
*   **Colores de Estado**:
    *   🟢 **Verde**: Encendido y funcionando.
    *   🔘 **Gris**: Apagado.
    *   🔵 **Azul**: Procesando (Arrancando o Reiniciando).

---

## 📄 Créditos y Soporte
Desarrollado para la monitorización de infraestructura crítica. Si encuentras un error, por favor abre un *Issue* en el repositorio.