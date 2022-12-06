const myWidget = cloudinary.createUploadWidget(
    {
        cloudName: 'dpwaxzhnx',
        uploadPreset: 'tkxeggub',
        autoMinimize: true,
        resourceType: 'image',
        cropping: true,
        croppingValidateDimensions: true,
        showSkipCropButton: false,
        croppingShowDimensions: true,
        maxImageWidth: 500,
        maxImageHeight: 500,
        croppingCoordinatesMode: 'custom',
        styles: {
            palette: {
                window: "#000",
                windowBorder: "#b96acb",
                tabIcon: "#b96acb",
                menuIcons: "#b96acb",
                textDark: "#FFFFFF",
                textLight: "#000000",
                link: "#ffc107",
                action: "#FF620C",
                inactiveTabIcon: "#b96acb",
                error: "#F44235",
                inProgress: "#ffc107",
                complete: "#20B832",
                sourceBg: "#1f1e1e"
            },
            frame: {
                background: "rgba(0, 0, 0, 0.8)"
            }
        }
    },
    (error, result) => {
        if (!error && result && result.event === "success") {
            console.log("imagen cargada")
            document.getElementById("image").value = result.info.secure_url
        }
    }
);

document.getElementById("upload_widget").addEventListener(
    "click",
    function (element) {
        element.preventDefault();
        myWidget.open();
    }
);